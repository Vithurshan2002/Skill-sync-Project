<?php

namespace App\Filament\Customer\Pages;

use App\Filament\Shared\GatewayPage;
use App\Filament\Shared\LocationFields;
use Filament\Forms\Components\DateTimePicker;
use Filament\Forms\Components\Select;
use Filament\Forms\Components\Textarea;
use Filament\Forms\Components\TextInput;
use Filament\Schemas\Schema;

class NewRequest extends GatewayPage
{
    protected static ?string $slug = 'requests/new';

    protected static ?string $title = 'What can we help with?';

    protected static ?string $navigationLabel = 'New request';

    protected static string|\BackedEnum|null $navigationIcon = 'heroicon-o-plus-circle';

    protected static ?int $navigationSort = 2;

    protected string $view = 'filament.customer.new-request';

    protected ?string $subheading = 'Describe the job. We’ll help you find the right skills.';

    public ?array $data = [];

    public function mount(): void
    {
        $category = request()->query('category');
        $this->form->fill(['town' => auth()->user()->town ?? 'Colombo', 'description' => request()->query('description', ''), 'category' => array_key_exists((string) $category, $this->categoryOptions()) ? $category : null]);
    }

    public function form(Schema $schema): Schema
    {
        return $schema->components([
            TextInput::make('title')->label('Give your request a title')->placeholder('Repair a leaking kitchen tap')->required()->minLength(5)->maxLength(120)->columnSpanFull(),
            Textarea::make('description')->label('Tell us about the job')->placeholder('My kitchen tap keeps leaking even when it is closed.')->rows(5)->required()->minLength(15)->maxLength(2000)->helperText('Include what needs fixing and any details a professional should know.')->columnSpanFull(),
            Select::make('category')->label('Service category (optional)')->options(fn () => $this->categoryOptions())->placeholder('Let AI suggest a category, or choose one')->helperText('Automatic suggestions support Plumbing, Electrical, Carpentry, and Welding. You can also choose one of these four services manually.')->columnSpanFull(),
            TextInput::make('town')->required()->maxLength(100)->placeholder('Colombo'),
            TextInput::make('address')->label('Address (optional)')->maxLength(250),
            DateTimePicker::make('preferredAt')->label('Preferred date and time')->seconds(false)->timezone('Asia/Colombo')->required()->after('now')->helperText('Sri Lanka time · Asia/Colombo'),
            TextInput::make('budgetLkr')->label('Budget (optional)')->numeric()->minValue(1)->prefix('LKR')->helperText('An indication of your budget, not a final quote.'),
            LocationFields::make(),
        ])->columns(2)->statePath('data');
    }

    public function save(): void
    {
        $data = $this->form->getState();
        $data['title'] = trim($data['title']);
        $data['description'] = trim($data['description']);
        $result = $this->perform(fn () => $this->gateway()->createRequest(auth()->user(), $data), 'data');
        if ($result) {
            $this->success('Your request is ready. Let’s find someone for the job.');
            $this->redirect('/customer/requests/'.$result['data']['id']);
        }
    }
}
