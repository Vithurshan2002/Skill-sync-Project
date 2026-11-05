<?php

namespace App\Filament\Shared;

use App\Contracts\SkillSyncGateway;
use Filament\Widgets\StatsOverviewWidget;
use Filament\Widgets\StatsOverviewWidget\Stat;

class WorkspaceStats extends StatsOverviewWidget
{
    protected ?string $pollingInterval = null;

    public static function canView(): bool
    {
        return auth()->check() && in_array(auth()->user()->role, ['customer', 'worker'], true);
    }

    protected function getStats(): array
    {
        abort_unless(static::canView(), 403);
        $user = auth()->user();
        $data = app(SkillSyncGateway::class)->dashboard($user)['data'];
        $counts = $data['bookingsByStatus'];

        return $user->role === 'customer' ? [
            Stat::make('Service requests', $data['requests'])->description('Every job starts here')->icon('heroicon-o-clipboard-document-list'),
            Stat::make('Active bookings', ($counts['pending'] ?? 0) + ($counts['accepted'] ?? 0) + ($counts['in_progress'] ?? 0) + ($counts['awaiting_confirmation'] ?? 0))->description('Moving things forward')->icon('heroicon-o-calendar-days'),
            Stat::make('Completed jobs', $counts['completed'] ?? 0)->description('A few things taken care of')->icon('heroicon-o-check-circle'),
        ] : [
            Stat::make('Awaiting your response', $counts['pending'] ?? 0)->description('New opportunities')->icon('heroicon-o-inbox'),
            Stat::make('On your schedule', ($counts['accepted'] ?? 0) + ($counts['in_progress'] ?? 0) + ($counts['awaiting_confirmation'] ?? 0))->description('Accepted and active work')->icon('heroicon-o-calendar-days'),
            Stat::make('Completed bookings', $counts['completed'] ?? 0)->description('Your completed jobs')->icon('heroicon-o-check-circle'),
        ];
    }
}
