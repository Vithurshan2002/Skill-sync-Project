<?php

namespace App\Filament\Worker\Pages;

use App\Filament\Shared\GatewayPage;
use Filament\Actions\Action;
use Filament\Forms\Components\Textarea;
use Livewire\Attributes\Locked;

class JobDetails extends GatewayPage
{
    protected static string $role = 'worker';

    protected static ?string $slug = 'jobs/{bookingId}';

    protected static ?string $title = 'Job details';

    protected static bool $shouldRegisterNavigation = false;

    protected string $view = 'filament.shared.booking-details';

    #[Locked]
    public string $bookingId;

    public function mount(string $bookingId): void
    {
        $this->bookingId = $bookingId;
        $this->gateway()->booking(auth()->user(), $bookingId);
    }

    protected function getViewData(): array
    {
        return ['booking' => $this->gateway()->booking(auth()->user(), $this->bookingId)['data'], 'area' => 'worker'];
    }

    public function transitionAction(): Action
    {
        return Action::make('transition')->label('Update job')->requiresConfirmation()
            ->modalHeading(fn (array $arguments) => match ($arguments['status'] ?? '') {
                'accepted' => 'Accept this job and its deadline?', 'rejected' => 'Decline this job?', 'in_progress' => 'Start this job?', 'awaiting_confirmation' => 'Request customer completion confirmation?', 'cancelled' => 'Cancel this job?', default => 'Update this job?',
            })
            ->modalDescription('The customer will receive an update. Only the next valid step can be applied.')
            ->schema(fn (array $arguments): array => [Textarea::make('note')->label('Note (required for cancellation)')->required(($arguments['status'] ?? '') === 'cancelled')->minLength(5)->maxLength(500)])
            ->action(function (array $data, array $arguments) {
                $result = $this->perform(fn () => $this->gateway()->transitionBooking(auth()->user(), $this->bookingId, $arguments['status'], $data['note'] ?? null), $this->getMountedActionSchema()->getStatePath());
                if ($result) {
                    $this->success('Job updated. The customer has been notified.');
                }
            });
    }
}
