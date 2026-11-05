<?php

namespace App\DTOs;

final readonly class Notification extends DataTransferObject
{
    public function __construct(public string $id, public string $userId, public string $message, public string $targetPath, public string $createdAt, public ?string $readAt = null) {}
}
