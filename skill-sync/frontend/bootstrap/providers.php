<?php

use App\Providers\AppServiceProvider;
use App\Providers\Filament\AdminPanelProvider;
use App\Providers\Filament\CustomerPanelProvider;
use App\Providers\Filament\WorkerPanelProvider;
use App\Providers\SkillSyncServiceProvider;

return [
    AppServiceProvider::class,
    SkillSyncServiceProvider::class,
    CustomerPanelProvider::class,
    WorkerPanelProvider::class,
    AdminPanelProvider::class,
];
