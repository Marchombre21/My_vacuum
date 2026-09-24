#![no_std]
#![no_main]
#![deny(
    clippy::mem_forget,
    reason = "mem::forget is generally not safe to do with esp_hal types, especially those \
    holding buffers for the duration of a data transfer."
)]
#![deny(clippy::large_stack_frames)]

use defmt::info;
use embassy_embedded_hal::shared_bus::asynch::i2c::I2cDevice;
use embassy_executor::Spawner;
use embassy_sync::blocking_mutex::raw::NoopRawMutex;
use embassy_sync::mutex::Mutex;
use embassy_time::{Duration, Timer};
use embedded_graphics::prelude::*;
use embedded_graphics::{
    mono_font::{MonoTextStyleBuilder, ascii::FONT_6X10},
    pixelcolor::BinaryColor,
    text::{Baseline, Text},
};
use embedded_hal_async::i2c::I2c as _;
use esp_hal::clock::CpuClock;
use esp_hal::i2c::master::{Config as I2cConfig, I2c};
use esp_hal::time::Rate;
use esp_hal::timer::timg::TimerGroup;

use core::fmt::Write;
use esp_println as _;
use heapless::String;
use ssd1306::{I2CDisplayInterface, Ssd1306Async, prelude::*};

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

    // Au démarrage, le mpu 6500 est en mode veille et c'est le registre 0x6B qui contrôle ça. En écrivant 0x00 sur ce registre, ça met donc les 8 bits de ce registre à 0 et ça désactive donc le mode veille.
    match i2c_bus.write(MPU_ADDR, &[0x6B, 0x00]) {
        Err(_) => {
            info!("MPU not launched")
        }
        Ok(_) => {
            info!("MPU launched")
        }
    }

    // J'ai besoin du bus pour deux composants (l'écran et le capteur) donc je dois utiliser le I2cDevice pour pouvoir le partager.
    // Et, évidemment, un mutex est nécessaire pour ne pas l'utiliser au même moment. Le mutex nécessite un RawMutex bloquant. C'est lui
    // qui garde l'accès à la valeur. Il y a le choix entre trois différents : CriticalSectionRawMutex when data can be shared between threads and interrupts.
    // NoopRawMutex when data is only shared between tasks running on the same executor.
    // ThreadModeRawMutex when data is shared between tasks running on the same executor but you want a singleton.
    let mut_i2c_bus = Mutex::<NoopRawMutex, _>::new(i2c_bus);
    // I2cDevice instancie un 'service' I2C qui partage un bus. Pour avoir accès aux méthodes inhérentes au trait I2C je dois importer le trait via embedded_hal_async
    // sinon les méthodes ne sont pas trouvées.
    let display_i2c = I2cDevice::new(&mut_i2c_bus);
    let mut gyro_i2c = I2cDevice::new(&mut_i2c_bus);

    let interface = I2CDisplayInterface::new(display_i2c);
    let mut display = Ssd1306Async::new(interface, DisplaySize128x64, DisplayRotation::Rotate0)
        .into_buffered_graphics_mode();
    let mut registers;
    let first_register = [0x3B];

    // Valeurs par défaut du composant, je pourrais les changer en écrivant sur les registres 1B et 1C mais il n'y a pas l'utilité ici.
    let gyro_sensitivity = 131.0;
    let accel_sensitivity = 16384.0;
    let text_style = MonoTextStyleBuilder::new()
        .font(&FONT_6X10)
        .text_color(BinaryColor::On)
        .build();
    let mut buffer: String<128> = String::new();
    display.init().await.unwrap();

    loop {
        registers = [0_u8; 14];
        // MPU_ADDR cible le slave, first_register indique à l'esclave l'adresse du registre sur lequel écrire mais, comme le master envoie un signal 'repeated start', il passe en mode
        // lecture et le slave va envoyer les données contenues sur le registre sur lequel il est (0x3B en l'occurrence) qui sont sur 8 bits. Ça va donc remplir le premier élément
        // de mon buffer registers. Mais tant que le buffer ne sera pas rempli, le slave devra continuer de le remplir avec les données de ses registres. Il va donc incrémenter
        // son pointeur de registre de 1 et remplir le 2e emplacement de mon buffer et ainsi de suite jusqu'à ce que j'ai le résultat des 14 registres voulus (vu qu'ils sont côte à
        // côte dans la liste des registres).
        gyro_i2c
            .write_read(MPU_ADDR, &first_register, &mut registers)
            .await
            .unwrap();

        // Ici je convertis ces données sur 8 bits en données sur 16 bits. Donc 11111111 deviendra 00000000 11111111.
        // Je déplace ensuite tous les bits de la variable de 8 bits vers la gauche. Donc les bits de poid fort retrouvent leur place à gauche. Et enfin
        // je rajoute les bits de poids faible avec un OU logique qui met un 1 SI au moins l'un des deux bits est 1.
        let accel_x = (registers[0] as i16) << 8 | (registers[1] as i16);
        let accel_y = (registers[2] as i16) << 8 | (registers[3] as i16);
        let accel_z = (registers[4] as i16) << 8 | (registers[5] as i16);
        let temp_raw = (registers[6] as i16) << 8 | (registers[7] as i16);
        let gyro_x = (registers[8] as i16) << 8 | (registers[9] as i16);
        let gyro_y = (registers[10] as i16) << 8 | (registers[11] as i16);
        let gyro_z = (registers[12] as i16) << 8 | (registers[13] as i16);

        let accel_x_exploit = accel_x as f64 / accel_sensitivity;
        let accel_y_exploit = accel_y as f64 / accel_sensitivity;
        let accel_z_exploit = accel_z as f64 / accel_sensitivity;
        let temp_raw_exploit = (temp_raw as f64 / 340.0) + 36.53;
        let gyro_x_exploit = gyro_x as f64 / gyro_sensitivity;
        let gyro_y_exploit = gyro_y as f64 / gyro_sensitivity;
        let gyro_z_exploit = gyro_z as f64 / gyro_sensitivity;

        buffer.clear();
        display.clear_buffer();

        write!(
            buffer,
            "A_X={:.1}, A_Y={:.1}\nA_Z={:.1}, T={:.1}\nG_X={:.1}, G_Y={:.1}\nG_Z={:.1}",
            accel_x_exploit,
            accel_y_exploit,
            accel_z_exploit,
            temp_raw_exploit,
            gyro_x_exploit,
            gyro_y_exploit,
            gyro_z_exploit
        ).unwrap();

        Text::with_baseline(&buffer, Point::new(0, 16), text_style, Baseline::Top)
            .draw(&mut display)
            .unwrap();

        display.flush().await.unwrap();
        Timer::after(Duration::from_millis(500)).await;
    }
}