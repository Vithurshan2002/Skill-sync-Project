<?php

namespace App\Filament\Worker\Pages;

use App\Filament\Shared\LocationFields;
use Filament\Forms\Components\CheckboxList;
use Filament\Forms\Components\Select;
use Filament\Forms\Components\TagsInput;
use Filament\Forms\Components\Textarea;
use Filament\Forms\Components\TextInput;
use Filament\Forms\Components\Toggle;
use Filament\Schemas\Components\Section;
use Filament\Schemas\Schema;

class Profile extends \App\Filament\Customer\Pages\Profile
{
    protected static string $role = 'worker';

    protected static ?string $title = 'Put your best work forward.';

    protected static ?string $navigationLabel = 'My profile';

    protected static ?int $navigationSort = 3;

    protected ?string $subheading = 'Help customers understand your skills, experience, and availability.';

    protected function getViewData(): array
    {
        return ['workerReview' => $this->gateway()->profile(auth()->user())['data']];
    }

    public function form(Schema $schema): Schema
    {
        return $schema->components([
            Section::make('Personal details')->icon('heroicon-o-user-circle')
                ->description('Keep your contact details accurate so customers can coordinate their bookings.')->schema([
                    TextInput::make('name')->required()->maxLength(100),
                    TextInput::make('town')->label('Your home town')->required()->maxLength(80),
                    TextInput::make('phone')->tel()->maxLength(30),
                    Select::make('contactPreference')->label('Contact preference')->options(['email' => 'Email', 'phone' => 'Phone'])->required(),
                ])->columns(2)->columnSpanFull(),
            Section::make('Skills and service areas')->icon('heroicon-o-wrench-screwdriver')
                ->description('Describe the work you do and the areas you serve.')->schema([
                    Textarea::make('bio')->label('About your work')->required()->minLength(15)->maxLength(2000)->rows(4)->columnSpanFull(),
                    CheckboxList::make('categories')->label('Service categories')->options(fn () => $this->categoryOptions())->required()->minItems(1)->columns(2)->columnSpanFull()->helperText('Choose the services you offer.'),
                    TagsInput::make('serviceTowns')->label('Towns you serve')->required()->rules(['array', 'min:1'])->suggestions(['Colombo', 'Jaffna', 'Kandy', 'Galle'])->helperText('Type a town and press Enter.')->columnSpanFull(),
                    TextInput::make('yearsExperience')->label('Years of experience')->integer()->minValue(0)->maxValue(60)->required(),
                ])->columns(2)->columnSpanFull(),
            Section::make('Rates and availability')->icon('heroicon-o-banknotes')
                ->description('Set your starting rate and let customers know if you are accepting work.')->schema([
                    TextInput::make('rateLkr')->label('Service rate')->numeric()->minValue(1)->prefix('LKR')->required(),
                    Select::make('rateUnit')->label('Rate basis')->options(['hour' => 'Per hour', 'visit' => 'Per visit'])->required(),
                    Toggle::make('available')->label('Available for new jobs')->helperText('Customers can filter by your availability.'),
                ])->columns(2)->columnSpanFull(),
            LocationFields::make(true)->icon('heroicon-o-map-pin'),
        ])->columns(2)->statePath('data');
    }
}
