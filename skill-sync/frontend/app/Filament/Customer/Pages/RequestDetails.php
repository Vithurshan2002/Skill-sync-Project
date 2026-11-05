<?php

namespace App\Filament\Customer\Pages;

use App\Filament\Shared\GatewayPage;
use App\Filament\Shared\LocationFields;
use Filament\Actions\Action;
use Filament\Forms\Components\DateTimePicker;
use Filament\Forms\Components\Textarea;
use Filament\Forms\Components\TextInput;
use Livewire\Attributes\Locked;

class RequestDetails extends GatewayPage
{
    protected static ?string $slug = 'requests/{requestId}';

    protected static ?string $title = 'Your service request';

    protected static bool $shouldRegisterNavigation = false;

    protected string $view = 'filament.customer.request-details';

    #[Locked]
    public string $requestId;

    public function mount(string $requestId): void
    {
        $this->requestId = $requestId;
        $this->gateway()->request(auth()->user(), $requestId);
    }

    protected function getViewData(): array
    {
        return ['requestRecord' => $this->gateway()->request(auth()->user(), $this->requestId)['data']];
    }

    public function editAction(): Action
    {
        return Action::make('edit')->label('Edit request')->icon('heroicon-o-pencil-square')
            ->modalHeading('Edit service request')->modalSubmitActionLabel('Save changes')
            ->modalContent(fn () => view('filament.shared.action-error', [
                'operationErrors' => $this->getErrorBag()->get($this->getMountedActionSchema()->getStatePath().'.operation'),
                'serviceError' => $this->gatewayError,
            ]))
            ->visible(fn (): bool => $this->gateway()->request(auth()->user(), $this->requestId)['data']['status'] === 'submitted')
            ->fillForm(fn (): array => $this->gateway()->request(auth()->user(), $this->requestId)['data'])
            ->schema([
                TextInput::make('title')->label('Request title')->required()->minLength(5)->maxLength(120)->columnSpanFull(),
                Textarea::make('description')->label('Tell us about the job')->rows(5)->required()->minLength(15)->maxLength(2000)->columnSpanFull(),
                TextInput::make('town')->required()->maxLength(100),
                TextInput::make('address')->label('Address (optional)')->maxLength(250),
                DateTimePicker::make('preferredAt')->label('Preferred date and time')->seconds(false)->timezone('Asia/Colombo')->required()->after('now')->helperText('Sri Lanka time · Asia/Colombo'),
                TextInput::make('budgetLkr')->label('Budget (optional)')->numeric()->minValue(1)->prefix('LKR'),
                LocationFields::make(),
            ])
            ->action(function (array $data, Action $action): void {
                $data['title'] = trim($data['title']);
                $data['description'] = trim($data['description']);
                $result = $this->perform(
                    fn () => $this->gateway()->updateRequest(auth()->user(), $this->requestId, $data),
                    $this->getMountedActionSchema()->getStatePath(),
                );
                if (! $result) {
                    $action->halt();
                }
                $this->success('Request updated. You can now find suitable workers.');
            });
    }

    public function findWorkers(): void
    {
        $record = $this->gateway()->request(auth()->user(), $this->requestId)['data'];
        if ($record['category']) {
            $this->redirect('/customer/requests/'.$this->requestId.'/recommendations');

            return;
        }
        $this->redirect('/customer/requests/'.$this->requestId.'/recommendations');
    }
}
