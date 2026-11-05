<?php

namespace App\DTOs;

final readonly class Review extends DataTransferObject
{
    public function __construct(public string $id, public string $bookingId, public string $customerId, public string $workerId, public int $rating, public string $comment, public string $createdAt) {}
}
