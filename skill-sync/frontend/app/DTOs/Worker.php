<?php

namespace App\DTOs;

final readonly class Worker extends DataTransferObject
{
    public function __construct(public string $id, public string $name, public string $town, public array $serviceTowns, public array $categories, public string $bio, public int $yearsExperience, public float $rateLkr, public string $rateUnit, public bool $available, public ?float $rating, public int $reviewCount, public array $performance, public ?float $reliabilityProbability, public bool $verified) {}
}
