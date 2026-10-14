import math

from aspi_odometry.aspiodom import Odom

import pytest


def test_tout_droit():
    # Les deux roues avancent de 1 m : le robot avance de 1 m sans tourner.
    distance, rotation = Odom.odom_dist_rot(1.0, 1.0, 0.2)
    assert distance == pytest.approx(1.0)
    assert rotation == pytest.approx(0.0)


def test_rotation_sur_place():
    # Roues en sens inverse : le robot tourne sans avancer.
    # Rotation = (0.1 - (-0.1)) / 0.2 = 1 radian (environ 57°).
    distance, rotation = Odom.odom_dist_rot(-0.1, 0.1, 0.2)
    assert distance == pytest.approx(0.0)
    assert rotation == pytest.approx(1.0)


def test_avance_vers_x():
    # Robot orienté à 0 rad qui avance de 1 m : x augmente, y ne bouge pas.
    x, y = Odom.odom_steps(1.0, 0.0, 0.0, 0.0, 0.0)
    assert x == pytest.approx(1.0)
    assert y == pytest.approx(0.0)


def test_avance_vers_y():
    # Robot tourné d'un quart de tour (π/2) qui avance de 1 m : y augmente.
    # Ce test attrape un cos/sin inversé.
    x, y = Odom.odom_steps(1.0, 0.0, math.pi / 2, 0.0, 0.0)
    assert x == pytest.approx(0.0, abs=1e-9)
    assert y == pytest.approx(1.0)

    # Robot tourné d'un quart de tour (π/2) qui avance de 1 m : y augmente.
    # Ce test attrape un cos/sin inversé.
    x, y = Odom.odom_steps(1.0, 0.0, math.pi / 2, 0.0, 0.0)
    assert x == pytest.approx(0.0, abs=1e-9)
    assert y == pytest.approx(1.0)


def test_part_de_la_position_actuelle():
    # Le déplacement s'ajoute à la position de départ.
    x, y = Odom.odom_steps(1.0, 0.0, 0.0, 2.0, 3.0)
    assert x == pytest.approx(3.0)
    assert y == pytest.approx(3.0)


def test_quaternion_zero():
    q = Odom.yaw_to_quaternion(0.0)
    assert (q.x, q.y, q.z, q.w) == pytest.approx((0.0, 0.0, 0.0, 1.0))


def test_quaternion_demi_tour():
    # θ = π (demi-tour) : z = sin(π/2) = 1, w = cos(π/2) = 0.
    q = Odom.yaw_to_quaternion(math.pi)
    assert q.z == pytest.approx(1.0)
    assert q.w == pytest.approx(0.0, abs=1e-9)
