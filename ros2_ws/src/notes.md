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

# Matériel

## Encodeurs des roues (fils jaune et vert)

    À l'arrière de chaque moteur, il y a un petit disque aimanté et deux capteurs magnétiques (capteurs à effet Hall).
    Chaque fois qu'un pôle de l'aimant passe devant un capteur, il envoie une impulsion : 11 impulsions par tour du moteur.

### Quadrature : savoir dans quel sens tourne la roue
    Les deux capteurs (canal A = jaune, canal B = vert) sont légèrement décalés : l'un voit l'aimant un peu avant l'autre.
    - A change avant B : la roue tourne dans un sens.
    - B change avant A : elle tourne dans l'autre sens.
    Le compteur matériel de l'ESP32 (PCNT) fait ce raisonnement tout seul : il ajoute 1 dans un sens, retire 1 dans l'autre.

### ×4 : quatre fois plus de précision
    Chaque impulsion a un front montant (le signal passe de 0 à 1) et un front descendant (de 1 à 0), sur chacun des deux canaux.
    En comptant tous les fronts : 11 × 4 = 44 comptes par tour de moteur.

### Du moteur à la roue : le rapport de réduction
    Les engrenages ralentissent la rotation : avec un rapport de 1/30, le moteur fait 30 tours pendant que la roue en fait 1.
    Comptes par tour de roue = 44 × rapport.  (Mon rapport : encore inconnu.)
    Tour de roue = π × 65 mm ≈ 204 mm (π ≈ 3,14 : le nombre qui passe de la largeur d'un cercle à son tour complet).
    Exemple avec un rapport de 30 : 44 × 30 = 1320 comptes par tour, donc 204 ÷ 1320 ≈ 0,15 mm par compte.

### Alimentation (fils bleu et noir)
    En 3,3 V et pas en 5 V : les signaux montent à peu près à la tension d'alimentation, et les broches de l'ESP32 supportent 3,3 V au maximum.

## Driver de moteurs L298N

    L'ESP32 ne peut pas alimenter un moteur par ses broches : il donne des ordres au L298N, qui envoie le courant de la batterie aux moteurs.
    Un module pilote 2 moteurs : moteur gauche sur OUT1/OUT2, moteur droit sur OUT3/OUT4 (fils rouge et blanc).

### Les entrées (venant de l'ESP32)
    - IN1/IN2 : le sens du moteur A (IN1=1, IN2=0 → un sens ; IN1=0, IN2=1 → l'autre ; les deux à 0 → arrêt).
    - IN3/IN4 : pareil pour le moteur B.
    - ENA/ENB : la vitesse. On enlève le cavalier de ENA/ENB et on y envoie un signal PWM : l'ESP32 allume et éteint
      très vite ; allumé la moitié du temps = environ la moitié de la vitesse.
    Le 3,3 V de l'ESP32 suffit pour ces entrées.

### Le régulateur 78M05 et son cavalier
    - Cavalier en place et batterie jusqu'à 12 V : la carte fabrique elle-même son 5 V, et la borne « +5V » est une SORTIE.
      Ne jamais y brancher une autre alimentation 5 V dans ce cas.
    - Batterie au-dessus de 12 V : enlever le cavalier et fournir le 5 V soi-même sur cette borne.

### À savoir
    - Le L298N « mange » environ 2 V : avec une batterie de 12 V, les moteurs reçoivent environ 10 V. Cette perte se transforme en chaleur.
    - La masse (GND) doit être commune entre la batterie, le L298N et l'ESP32, sinon les ordres ne sont pas compris.

# Odométrie

    But : savoir où est le robot (x, y en mètres) et vers où il regarde (θ, « thêta », en radians), par rapport au départ.
    x = devant au départ, y = à gauche, θ positif = tourné vers la gauche.
    Un tour = 2π ≈ 6,28 rad, un demi-tour = π, un quart de tour = π/2.
    Principe : à chaque message, calculer le petit déplacement depuis le message précédent et l'ajouter (comme compter ses pas).

## 1. De l'angle de la roue à la distance
    distance = angle (rad) × rayon de la roue   (rayon = 0,0325 m)
    Un tour (2π rad) fait avancer du périmètre (2π × rayon), donc 1 rad fait avancer de 1 × rayon.

## 2. Ne garder que ce qui a changé
    /joint_states donne l'angle total depuis le démarrage : faire la différence avec l'angle du message précédent.
    Premier message : on mémorise seulement, sans calculer.

## 3. Avance et rotation
    d  = (d_gauche + d_droite) / 2              → l'avance du centre (la moyenne)
    Δθ = (d_droite − d_gauche) / écartement     → la rotation (Δ = « le petit changement de »)
    Pourquoi : en tournant sur place, chaque roue fait un cercle de rayon écartement/2 autour du centre,
    et angle = distance ÷ rayon (l'étape 1 à l'envers).
    Exemples (écartement 0,20 m) : 1 cm / 1 cm → tout droit ; −1 cm / 1 cm → tourne sur place de 0,1 rad (≈ 6°) à gauche.
    Un écartement faux n'abîme pas les lignes droites, seulement les virages.

## 4. Répartir l'avance entre x et y
    Δx = d × cos(θ)      Δy = d × sin(θ)       (math.cos et math.sin en Python)
    cos et sin = la part de l'avance qui va vers x et celle qui va vers y :
    θ = 0 → tout sur x ; θ = π/2 (90°) → tout sur y ; θ = π/4 (45°) → 0,707 de chaque ; θ = π → on recule sur x.
    Plus précis : utiliser la direction du milieu du mouvement, θ + Δθ/2, dans cos et sin.
    Puis : x += Δx, y += Δy, θ += Δθ.

## 5. Les vitesses
    dt = temps du message − temps du message précédent (prendre header.stamp, pas l'heure de réception)
    vitesse avant = d / dt (m/s), vitesse de rotation = Δθ / dt (rad/s).

## Ce qu'on publie
    - nav_msgs/Odometry sur /odom : repère « odom » (le départ), qui décrit « base_link » (le robot).
    - La transformation TF odom → base_link, avec les mêmes x, y, θ (utilisée par RViz et slam_toolbox).
    - L'angle est rangé dans un « quaternion » (4 nombres pour une orientation en 3D). Robot à plat :
      x = 0, y = 0, z = sin(θ/2), w = cos(θ/2).

## Test avec fake_esp32.py
    +5 impulsions par paquet sur chaque roue → 5 / 1980 × 2π ≈ 0,0159 rad → × 0,0325 ≈ 0,5 mm par paquet.
    Les deux roues pareilles → ligne droite : x grandit d'environ 5 cm/s, y et θ restent à 0.

## Limite
    Les petites erreurs (patinage, écartement approximatif) s'additionnent : l'odométrie seule dérive.
    L'IMU (robot_localization) et le lidar (slam_toolbox) corrigeront plus tard.
