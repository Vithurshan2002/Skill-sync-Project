<?php

namespace App\Filament\Worker\Pages;

use App\Filament\Shared\GatewayPage;

class Performance extends GatewayPage
{
    protected static string $role = 'worker';

    protected static ?string $slug = 'performance';

    protected static ?string $title = 'A view of your work.';

    protected static ?string $navigationLabel = 'Performance';

    protected static string|\BackedEnum|null $navigationIcon = 'heroicon-o-chart-bar';

    protected static ?int $navigationSort = 4;

    protected string $view = 'filament.worker.performance';

    protected ?string $subheading = 'Category-specific work history and customer feedback.';

    protected function getViewData(): array
    {
        return ['performanceData' => $this->gateway()->performance(auth()->user())['data']];
    }
}
