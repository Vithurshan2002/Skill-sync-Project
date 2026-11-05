<?php

namespace App\Filament\Shared;

use Filament\AvatarProviders\Contracts\AvatarProvider;
use Illuminate\Database\Eloquent\Model;

class InitialsAvatarProvider implements AvatarProvider
{
    public function get(Model $record): string
    {
        $initials = collect(preg_split('/\s+/u', trim($record->name)))
            ->take(2)->map(fn (string $part): string => mb_strtoupper(mb_substr($part, 0, 1)))->join('');
        $text = htmlspecialchars($initials, ENT_XML1 | ENT_QUOTES, 'UTF-8');
        $svg = '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 80 80"><rect width="80" height="80" rx="40" fill="#eeedff"/><text x="40" y="42" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="26" font-weight="600" fill="#5145cd">'.$text.'</text></svg>';

        return 'data:image/svg+xml;base64,'.base64_encode($svg);
    }
}
