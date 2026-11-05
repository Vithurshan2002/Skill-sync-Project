<?php

namespace App\Filament\Admin\Pages;

use App\Filament\Shared\GatewayPage;
use Filament\Actions\Action;

class Dashboard extends GatewayPage
{
    protected static string $role = 'admin';

    protected static ?string $slug = 'dashboard';

    protected static ?string $title = 'Administration';

    protected static ?string $navigationLabel = 'Overview';

    protected static string|\BackedEnum|null $navigationIcon = 'heroicon-o-squares-2x2';

    protected static ?int $navigationSort = 1;

    protected string $view = 'filament.admin.dashboard';

    protected ?string $subheading = 'Manage workers, customers, services, and bookings.';

    protected function getViewData(): array
    {
        $dashboard = $this->gateway()->dashboard(auth()->user())['data'];
        $counts = $dashboard['counts'];
        $models = $dashboard['models'] ?? [];

        $evaluation = $dashboard['evaluation'] ?? null;
        $pendingApplications = $dashboard['pendingApplications'] ?? 0;

        return compact('counts', 'models', 'evaluation', 'pendingApplications');
    }

    protected function getHeaderActions(): array
    {
        return [Action::make('exportTraining')->label('Export real training outcomes')
            ->action(function () {
                $result = $this->gateway()->trainingDataset(auth()->user())['data'];

                return response()->streamDownload(function () use ($result): void {
                    echo json_encode($result, JSON_PRETTY_PRINT | JSON_THROW_ON_ERROR);
                }, 'skillsync-real-outcomes-'.now()->format('Ymd-His').'.json', ['Content-Type' => 'application/json']);
            })];
    }
}
