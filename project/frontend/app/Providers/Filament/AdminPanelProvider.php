<?php

namespace App\Providers\Filament;

use App\Filament\Admin\Pages;
use Filament\Panel;

class AdminPanelProvider extends SkillSyncPanelProvider
{
    public function panel(Panel $panel): Panel
    {
        return $this->shared($panel, 'admin')->pages([
            Pages\Dashboard::class, Pages\Records::class,
        ]);
    }
}
