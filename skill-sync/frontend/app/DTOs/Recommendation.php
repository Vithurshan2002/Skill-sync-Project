<?php

namespace App\DTOs;

use App\Enums\PredictionSource;

final readonly class Recommendation extends DataTransferObject
{
    public function __construct(public string $workerId, public int $rank, public ?float $matchScore, public ?float $categorySkillScore, public ?float $reliabilityProbability, public array $reasons, public PredictionSource $source) {}
}
