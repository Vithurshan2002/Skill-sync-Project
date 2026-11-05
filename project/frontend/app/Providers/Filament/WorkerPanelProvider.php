<?php

namespace App\Providers\Filament;

use App\Filament\Worker\Pages;
use Filament\Panel;

class WorkerPanelProvider extends SkillSyncPanelProvider
{
    public function panel(Panel $panel): Panel
    {
        return $this->shared($panel, 'worker')->pages([
            Pages\Dashboard::class, Pages\Jobs::class, Pages\JobDetails::class,
            Pages\Profile::class, Pages\Performance::class,
        ]);
    }
}
