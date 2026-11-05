<?php

namespace App\Enums;

enum BookingStatus: string
{
    case Pending = 'pending';
    case Accepted = 'accepted';
    case InProgress = 'in_progress';
    case AwaitingConfirmation = 'awaiting_confirmation';
    case Completed = 'completed';
    case Rejected = 'rejected';
    case Cancelled = 'cancelled';

    public function isActive(): bool
    {
        return in_array($this, [self::Pending, self::Accepted, self::InProgress, self::AwaitingConfirmation], true);
    }
}
