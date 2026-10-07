#![no_std]
#![no_main]
#![deny(
    clippy::mem_forget,
    reason = "mem::forget is generally not safe to do with esp_hal types, especially those \
    holding buffers for the duration of a data transfer."
)]
#![deny(clippy::large_stack_frames)]

use defmt::info;
use embassy_executor::Spawner;
use embassy_time::{Duration, Ticker};
use esp_hal::clock::CpuClock;
use esp_hal::i2c::master::{Config as I2cConfig, I2c};
use esp_hal::time::Rate;
use esp_hal::timer::timg::TimerGroup;
use esp_hal::uart::{Config, Uart};
use esp_hal::gpio::{Input, InputConfig, Pull, interconnect::InputSignal};
use esp_hal::pcnt::{
    channel::{CtrlMode, EdgeMode},
    unit::Unit,
    Pcnt
};

use esp_println as _;

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}

esp_bootloader_esp_idf::esp_app_desc!();

const MPU_ADDR: u8 = 0x68;

#[allow(
    clippy::large_stack_frames,
    reason = "it's not unusual to allocate larger buffers etc. in main"
)]
#[esp_rtos::main]
async fn main(spawner: Spawner) -> ! {
    let config = esp_hal::Config::default().with_cpu_clock(CpuClock::max());
    let peripherals = esp_hal::init(config);

    let timg0 = TimerGroup::new(peripherals.TIMG0);
    let sw_interrupt =
        esp_hal::interrupt::software::SoftwareInterruptControl::new(peripherals.SW_INTERRUPT);
    esp_rtos::start(timg0.timer0, sw_interrupt.software_interrupt0);

    let _ = spawner;

    let mut i2c_bus = I2c::new(
        peripherals.I2C0,
        I2cConfig::default().with_frequency(Rate::from_khz(400)),
    )
    .unwrap()
    .with_scl(peripherals.GPIO18)
    .with_sda(peripherals.GPIO23)
    .into_async();

    let mut uart2 = Uart::new(peripherals.UART2, Config::default())
        .unwrap()
        .with_rx(peripherals.GPIO16)
        .with_tx(peripherals.GPIO17)
        .into_async();
    
    let enc_config = InputConfig::default().with_pull(Pull::Up);
    let left_a = Input::new(peripherals.GPIO25, enc_config);
    let left_b = Input::new(peripherals.GPIO26, enc_config);
    let right_a = Input::new(peripherals.GPIO32, enc_config);
    let right_b = Input::new(peripherals.GPIO33, enc_config);

    let pcnt = Pcnt::new(peripherals.PCNT);

    setup_quadrature(&pcnt.unit0, left_a.peripheral_input(), left_b.peripheral_input());
    setup_quadrature(&pcnt.unit1, right_a.peripheral_input(), right_b.peripheral_input());

    // Au démarrage, le mpu 6500 est en mode veille et c'est le registre 0x6B qui contrôle ça. En écrivant 0x00 sur ce registre, ça met donc les 8 bits de ce registre à 0 et ça désactive donc le mode veille.
    match i2c_bus.write_async(MPU_ADDR, &[0x6B, 0x00]).await {
        Err(_) => {
            info!("MPU not launched")
        }
        Ok(_) => {
            info!("MPU launched")
        }
    }

    let mut registers;
    let first_register = [0x3B];

    let mut packet = [0u8; 25];
    let mut ticker = Ticker::every(Duration::from_millis(10));

    let mut left_last = pcnt.unit0.value();
    let mut left_total: i32 = 0;
    let mut right_last = pcnt.unit1.value();
    let mut right_total: i32 = 0;

    loop {
        registers = [0_u8; 14];
        // MPU_ADDR cible le slave, first_register indique à l'esclave l'adresse du registre sur lequel écrire mais, comme le master envoie un signal 'repeated start', il passe en mode
        // lecture et le slave va envoyer les données contenues sur le registre sur lequel il est (0x3B en l'occurrence) qui sont sur 8 bits. Ça va donc remplir le premier élément
        // de mon buffer registers. Mais tant que le buffer ne sera pas rempli, le slave devra continuer de le remplir avec les données de ses registres. Il va donc incrémenter
        // son pointeur de registre de 1 et remplir le 2e emplacement de mon buffer et ainsi de suite jusqu'à ce que j'ai le résultat des 14 registres voulus (vu qu'ils sont côte à
        // côte dans la liste des registres).
        i2c_bus
            .write_read_async(MPU_ADDR, &first_register, &mut registers)
            .await
            .unwrap();

        let mut now = pcnt.unit0.value();
        left_total = left_total.wrapping_add(now.wrapping_sub(left_last) as i32);
        left_last = now;

        now = pcnt.unit1.value();
        right_total = right_total.wrapping_add(now.wrapping_sub(right_last) as i32);
        right_last = now;
        
        // On place deux octets de 'démarrage' au début pour que la réception sache quand commencer la lecture.
        packet[0] = 0xAA;
        packet[1] = 0x55;
        packet[2..16].copy_from_slice(&registers);
        packet[16..20].copy_from_slice(&left_total.to_be_bytes());
        packet[20..24].copy_from_slice(&right_total.to_be_bytes());
        
        let mut checksum: u8 = 0;
        for b in &packet[2..24] {
            checksum = checksum.wrapping_add(*b);
        }
        packet[24] = checksum;

        let mut sent = 0;
        while sent < packet.len() {
            sent += uart2.write_async(&packet[sent..]).await.unwrap();
        }
        ticker.next().await;
    }
}

fn setup_quadrature<const N: usize>(unit: &Unit<'_, N>, a: InputSignal, b: InputSignal) {
    unit.set_filter(Some(800)).unwrap();
    unit.clear();

    let ch0 = &unit.channel0;
    ch0.set_ctrl_signal(a.clone());
    ch0.set_edge_signal(b.clone());
    ch0.set_ctrl_mode(CtrlMode::Reverse, CtrlMode::Keep);
    ch0.set_input_mode(EdgeMode::Increment, EdgeMode::Decrement);

    let ch1 = &unit.channel1;
    ch1.set_ctrl_signal(b);
    ch1.set_edge_signal(a);
    ch1.set_ctrl_mode(CtrlMode::Reverse, CtrlMode::Keep);
    ch1.set_input_mode(EdgeMode::Decrement, EdgeMode::Increment);

    unit.resume();
}