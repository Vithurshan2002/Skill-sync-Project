<?php

namespace App\Enums;

enum PredictionSource: string
{
    case RuleBased = 'rule_based';
    case Model = 'model';
}
