<?php

namespace App\DTOs;

use JsonSerializable;

abstract readonly class DataTransferObject implements JsonSerializable
{
    public function jsonSerialize(): array
    {
        return get_object_vars($this);
    }

    public function toArray(): array
    {
        return json_decode(json_encode($this, JSON_THROW_ON_ERROR), true, 512, JSON_THROW_ON_ERROR);
    }
}
