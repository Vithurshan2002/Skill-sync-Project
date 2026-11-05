<?php

namespace App\Providers;

use App\Contracts\SkillSyncGateway;
use App\Services\SkillSync\FastApiSkillSyncGateway;
use Illuminate\Support\ServiceProvider;

class SkillSyncServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->bind(SkillSyncGateway::class, FastApiSkillSyncGateway::class);
    }
}
