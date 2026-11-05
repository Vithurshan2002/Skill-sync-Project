<?php

namespace App\Livewire\Shared;

use Illuminate\View\View;
use Livewire\Attributes\Layout;
use Livewire\Component;

#[Layout('components.layout')]
class Settings extends Component
{
    public function render(): View
    {
        return view('livewire.shared.settings');
    }
}
