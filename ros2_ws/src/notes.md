# Aspi_imu_bridge

## Struct.unpack (ou pack)

    '>7h' : la recette de décodage
    struct.unpack reçoit une suite d'octets, et cette petite chaîne lui explique comment les découper et les transformer en nombres.
    Elle se lit en trois morceaux :

### h : « un entier sur 2 octets, avec signe »
    Chaque mesure de ton MPU fait 2 octets : c'est un i16 côté Rust. 2 octets permettent d'écrire des nombres de −32 768 à +32 767.
    Le h minuscule dit « avec signe », c'est-à-dire que les nombres peuvent être négatifs. C'est indispensable : quand le robot tourne dans l'autre sens,
    le gyroscope donne une valeur négative. (H majuscule voudrait dire « sans signe », de 0 à 65 535, et les valeurs négatives seraient mal lues.)

### 7 : « sept fois 
    Tu as 7 mesures : accel X/Y/Z, température, gyro X/Y/Z. Donc 7h signifie « 7 entiers de 2 octets », soit 14 octets en tout.
    C'est exactement ce que contient self.buffer[2:16] (de la case 2 à la case 15, ça fait 14). unpack exige que le compte tombe juste.
    Avec un octet de plus ou de moins, il refuse et plante.
    Il te renvoie les 7 nombres dans l'ordre. C'est pour ça que tu peux écrire accel_x, accel_y, ..., gyro_z = ..., et que l'ordre de tes
    noms doit correspondre à l'ordre des registres du MPU.

### > : « l'octet de poids fort en premier » (big‑endian)
    Un nombre sur 2 octets est coupé en deux morceaux : un « gros » et un « petit ». Prenons 1000. En hexa, ça s'écrit 03 E8 :
    - 03 est l'octet de poids fort, celui qui compte pour beaucoup (3 × 256 = 768) ;
    - E8 est l'octet de poids faible (232).
    - 768 + 232 = 1000.