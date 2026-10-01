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
use embassy_time::{Duration, Timer};
use esp_hal::clock::CpuClock;
use esp_hal::i2c::master::{Config as I2cConfig, I2c};
use esp_hal::time::Rate;
use esp_hal::timer::timg::TimerGroup;
use esp_hal::uart::{Uart, Config};

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

    let mut uart2 = Uart::new(
        peripherals.UART2,
        Config::default())
        .unwrap()
        .with_rx(peripherals.GPIO16)
        .with_tx(peripherals.GPIO17);

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

    let mut packet = [0u8; 16];


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

        packet[0] = 0xAA;
        packet[1] = 0x55;
        packet[2..].copy_from_slice(&registers);

        let mut sent = 0;
        while sent < packet.len() {
            sent += uart2.write(&packet[sent..]).unwrap();
        }

        Timer::after(Duration::from_millis(500)).await;
    }
}
