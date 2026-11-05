<?php

namespace App\Filament\Shared;

use Filament\Forms\Components\TextInput;
use Filament\Schemas\Components\Section;
use Filament\Schemas\Components\View;

class LocationFields
{
    public static function make(bool $worker = false): Section
    {
        $fields = [
            View::make('filament.shared.location-capture')->viewData(['forWorker' => $worker])->columnSpanFull(),
            TextInput::make('latitude')->label('Latitude')->numeric()->minValue(-90)->maxValue(90)->requiredWith($worker ? ['longitude', 'serviceRadiusKm'] : 'longitude'),
            TextInput::make('longitude')->label('Longitude')->numeric()->minValue(-180)->maxValue(180)->requiredWith('latitude'),
        ];
        if ($worker) {
            $fields[] = TextInput::make('serviceRadiusKm')->label('Service radius (km)')->numeric()->minValue(0.1)->maxValue(500)->requiredWith('latitude')->helperText('How far you can travel from this location (0.1 to 500 km).')->columnSpanFull();
        }

        return Section::make($worker ? 'Service location (optional)' : 'Job location (optional)')
            ->description($worker ? 'Your base location and travel radius help nearby customers find you. Changes require admin approval.' : 'Save the place where the work will happen to find professionals within their travel radius.')
            ->schema($fields)->columns(2)->columnSpanFull();
    }
}
