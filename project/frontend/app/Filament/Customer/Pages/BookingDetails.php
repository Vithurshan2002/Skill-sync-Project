<?php

namespace App\Filament\Customer\Pages;

use App\Filament\Shared\GatewayPage;
use Filament\Actions\Action;
use Filament\Forms\Components\Select;
use Filament\Forms\Components\Textarea;
use Livewire\Attributes\Locked;

class BookingDetails extends GatewayPage
{
    protected static ?string $slug = 'bookings/{bookingId}';

    protected static ?string $title = 'Booking details';

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
        return ['booking' => $this->gateway()->booking(auth()->user(), $this->bookingId)['data'], 'area' => 'customer'];
    }

    public function cancelAction(): Action
    {
        return Action::make('cancel')->label('Cancel booking')->color('danger')->outlined()->requiresConfirmation()
            ->modalHeading('Cancel this booking?')->modalDescription('Your professional will be notified. You can return to the request and book again.')
            ->schema([Textarea::make('note')->label('Cancellation reason')->required()->minLength(5)->maxLength(500)])
            ->action(function (array $data) {
                $result = $this->perform(fn () => $this->gateway()->transitionBooking(auth()->user(), $this->bookingId, 'cancelled', $data['note'] ?? null));
                if ($result) {
                    $this->success('Booking cancelled. Your request is available to book again.');
                }
            });
    }

    public function reviewAction(): Action
    {
        return Action::make('review')->label('Leave a review')->icon('heroicon-o-star')->modalHeading('How did the job go?')
            ->modalDescription('Your first name, rating, and review will be shown publicly on this professional’s profile. One review is allowed per completed booking.')
            ->schema([
                Select::make('rating')->options([5 => '5 — Excellent', 4 => '4 — Good', 3 => '3 — Okay', 2 => '2 — Could be better', 1 => '1 — Poor'])->required(),
                Textarea::make('comment')->label('Your review')->required()->minLength(5)->maxLength(1000)->rows(4),
            ])->action(function (array $data) {
                $result = $this->perform(fn () => $this->gateway()->reviewBooking(auth()->user(), $this->bookingId, $data));
                if ($result) {
                    $this->success('Thanks — your review has been saved.');
                }
            });
    }

    public function confirmCompletionAction(): Action
    {
        return Action::make('confirmCompletion')->label('Confirm completed')->color('success')->requiresConfirmation()
            ->modalDescription('Confirm that the work was finished at the reported time shown above. Your confirmation finalizes this booking.')
            ->action(function (): void {
                if ($this->perform(fn () => $this->gateway()->transitionBooking(auth()->user(), $this->bookingId, 'completed'))) {
                    $this->success('Completion confirmed. You can now leave a review.');
                }
            });
    }

    public function disputeCompletionAction(): Action
    {
        return Action::make('disputeCompletion')->label('Work is not complete')->color('warning')
            ->schema([Textarea::make('note')->label('What still needs to be done?')->required()->minLength(5)->maxLength(500)])
            ->action(function (array $data): void {
                if ($this->perform(fn () => $this->gateway()->transitionBooking(auth()->user(), $this->bookingId, 'in_progress', $data['note']))) {
                    $this->success('Returned to in progress. The professional has been notified.');
                }
            });
    }

    public function complaintAction(): Action
    {
        return Action::make('complaint')->label('Submit complaint')->color('danger')->outlined()
            ->modalDescription('An administrator will review your complaint. An unreviewed allegation does not count against the professional.')
            ->schema([Textarea::make('reason')->label('Describe the issue and supporting details')->required()->minLength(10)->maxLength(2000)->rows(5)])
            ->action(function (array $data): void {
                if ($this->perform(fn () => $this->gateway()->submitComplaint(auth()->user(), $this->bookingId, $data))) {
                    $this->success('Complaint submitted for review.');
                }
            });
    }
}
