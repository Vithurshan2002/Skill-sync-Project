<?php

namespace App\Enums;

enum Role: string
{
    case Customer = 'customer';
    case Worker = 'worker';
    case Admin = 'admin';
}
