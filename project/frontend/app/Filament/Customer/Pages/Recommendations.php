<?php

namespace App\Filament\Customer\Pages;

use App\Filament\Shared\GatewayPage;
use Filament\Actions\Action;
use Filament\Forms\Components\Checkbox;
use Filament\Forms\Components\DateTimePicker;
use Filament\Schemas\Components\Section;
use Filament\Schemas\Components\Utilities\Get;
use Livewire\Attributes\Locked;
use Symfony\Component\HttpKernel\Exception\HttpException;

class Recommendations extends GatewayPage
{
    protected static ?string $slug = 'requests/{requestId}/recommendations';

    protected static ?string $title = 'The right skills for your job.';

    protected static bool $shouldRegisterNavigation = false;

    protected string $view = 'filament.customer.recommendations';

    protected ?string $subheading = 'Explore the reasons, compare your options, and choose with confidence.';

    #[Locked]
    public string $requestId;

    public string $category = '';

    public string $maxRate = '';

    public array $comparison = [];

    public array $recommendations = [];

    #[Locked]
    public string $recommendationSource = 'rule_based';

    #[Locked]
    public ?string $classificationMessage = null;

    public function mount(string $requestId): void
    {
        $this->requestId = $requestId;
        $record = $this->gateway()->request(auth()->user(), $requestId)['data'];
        if (in_array($record['status'], ['booked', 'closed'])) {
            $this->redirect('/customer/requests/'.$requestId);

            return;
        }
        $this->category = $record['category'] ?? '';
        if (! $this->category) {
            try {
                $classification = $this->gateway()->classifyRequest(auth()->user(), $requestId)['data'];
                $this->category = $classification['category'] ?? '';
                $this->classificationMessage = $this->category
                    ? 'AI suggested '.$this->category.'. You can change the category below.'
                    : 'Choose a service category to continue. Automatic categorization could not identify this request.';
            } catch (HttpException $exception) {
                if ($exception->getStatusCode() < 500) {
                    throw $exception;
                }
                $this->classificationMessage = 'Automatic categorization is currently unavailable. Choose a service category to continue.';
            }
        }
        $this->refreshRecommendations();
    }

    public function refreshRecommendations(): void
    {
        $this->recommendations = [];
        $this->comparison = [];
        $this->recommendationSource = 'rule_based';
        if (! $this->category) {
            return;
        }
        $result = $this->perform(function () {
            $record = $this->gateway()->request(auth()->user(), $this->requestId)['data'];
            if ($record['category'] !== $this->category) {
                $this->gateway()->updateRequest(auth()->user(), $this->requestId, ['category' => $this->category]);
            }

            return $this->gateway()->recommendations(auth()->user(), $this->requestId, ['available' => true, 'maxRate' => $this->maxRate]);
        });
        if ($result) {
            $this->recommendations = $result['data']['recommendations'];
            $this->recommendationSource = $result['data']['source'] ?? 'rule_based';
        }
    }

    public function updatedCategory(): void
    {
        $this->classificationMessage = null;
        $this->refreshRecommendations();
    }

    public function updatedMaxRate(): void
    {
        $this->refreshRecommendations();
    }

    public function toggleCompare(string $workerId): void
    {
        if (! collect($this->recommendations)->contains('workerId', $workerId)) {
            return;
        }
        if (in_array($workerId, $this->comparison, true)) {
            $this->comparison = array_values(array_diff($this->comparison, [$workerId]));
        } elseif (count($this->comparison) < 3) {
            $this->comparison[] = $workerId;
        } else {
            $this->addError('comparison', 'You can compare up to three professionals.');
        }
    }

    public function bookAction(): Action
    {
        return Action::make('book')->label('Choose professional')->icon('heroicon-o-arrow-right')
            ->modalHeading('Confirm your booking')
            ->modalDescription(function (array $arguments) {
                $worker = $this->gateway()->worker($arguments['workerId'])['data'];

                return $worker['name'].' · LKR '.number_format($worker['rateLkr']).' per '.$worker['rateUnit'].'. This is a rate basis; the final job cost is agreed with the professional. Your booking starts as pending.';
            })
            ->schema([
                Section::make('Appointment time')->description('Choose when the work starts and is expected to finish.')->schema([
                    DateTimePicker::make('scheduledAt')->label('Appointment time')->seconds(false)->timezone('Asia/Colombo')->required()->after('now')->default(fn () => $this->gateway()->request(auth()->user(), $this->requestId)['data']['preferredAt'])->helperText('All times are shown in Asia/Colombo.'),
                    DateTimePicker::make('scheduledEndAt')->label('Expected end time')->seconds(false)->timezone('Asia/Colombo')->required()->after('scheduledAt')->helperText('Reserve the full time needed for this job. Overlapping bookings are not allowed, including pending requests.'),
                    Checkbox::make('customDeadline')->label('Set a different deadline')->default(false)->live()
                        ->helperText('The completion deadline is the expected end time unless you choose a different one. The professional agrees to these times by accepting.'),
                    DateTimePicker::make('deadlineAt')->label('Completion deadline')->seconds(false)->timezone('Asia/Colombo')
                        ->visible(fn (Get $get): bool => (bool) $get('customDeadline'))
                        ->required(fn (Get $get): bool => (bool) $get('customDeadline'))
                        ->afterOrEqual('scheduledEndAt')->helperText('Choose a deadline at or after the expected end time.'),
                ])->contained(false),
                Checkbox::make('confirmed')->label('I understand the rate basis and want to request this booking.')->accepted()->required(),
            ])->modalSubmitActionLabel('Confirm booking')
            ->action(function (array $data, array $arguments) {
                $data['deadlineAt'] = ($data['customDeadline'] ?? false) ? $data['deadlineAt'] : $data['scheduledEndAt'];
                $result = $this->perform(fn () => $this->gateway()->createBooking(auth()->user(), ['requestId' => $this->requestId, 'workerId' => $arguments['workerId'], 'scheduledAt' => $data['scheduledAt'], 'scheduledEndAt' => $data['scheduledEndAt'], 'deadlineAt' => $data['deadlineAt']]), $this->getMountedActionSchema()->getStatePath());
                if ($result) {
                    $this->success('Booking sent. Your professional can now respond.');
                    $this->redirect('/customer/bookings/'.$result['data']['id']);
                }
            });
    }

    protected function getViewData(): array
    {
        return [
            'requestRecord' => $this->gateway()->request(auth()->user(), $this->requestId)['data'],
            'categories' => $this->categoryOptions(),
            'compared' => collect($this->recommendations)->whereIn('workerId', $this->comparison)->all(),
        ];
    }
}
