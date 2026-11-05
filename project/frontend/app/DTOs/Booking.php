<?php

namespace App\DTOs;

use App\Enums\BookingStatus;

final readonly class Booking extends DataTransferObject
{
    public function __construct(public string $id, public string $requestId, public string $customerId, public string $workerId, public string $scheduledAt, public BookingStatus $status, public float $quotedRateLkr, public string $rateUnit, public array $history) {}
}
