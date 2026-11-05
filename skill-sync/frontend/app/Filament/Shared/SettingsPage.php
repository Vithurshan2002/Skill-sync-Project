<?php

namespace App\Filament\Shared;

use Filament\Facades\Filament;
use Filament\Pages\Page;

class SettingsPage extends Page
{
    protected static ?string $slug = 'settings';

    protected static ?string $title = 'Account settings';

    protected static ?string $navigationLabel = 'Settings';

    protected static string|\BackedEnum|null $navigationIcon = 'heroicon-o-cog-6-tooth';

    protected static ?int $navigationSort = 92;

    protected ?string $subheading = 'Manage your account and session.';

    protected string $view = 'filament.shared.settings-page';

    public static function canAccess(): bool
    {
        return auth()->check() && auth()->user()->role === Filament::getCurrentPanel()?->getId();
    }
}
