<?php

namespace App\DTOs;

final readonly class CategoryPerformance extends DataTransferObject
{
    public function __construct(public string $category, public ?int $skillScore, public int $completedJobs) {}
}
