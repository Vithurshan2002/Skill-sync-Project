<?php

namespace App\DTOs;

final readonly class Category extends DataTransferObject
{
    public function __construct(public string $id, public string $label, public string $slug, public string $icon, public string $description, public string $exampleRequest) {}
}
