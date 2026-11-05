<?php

namespace App\DTOs;

use App\Enums\RequestStatus;

final readonly class ServiceRequest extends DataTransferObject
{
    public function __construct(public string $id, public string $customerId, public string $title, public string $description, public string $town, public ?string $address, public string $preferredAt, public ?float $budgetLkr, public ?string $category, public RequestStatus $status, public string $createdAt) {}
}
