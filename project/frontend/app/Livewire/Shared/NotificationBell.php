<?php

namespace App\Livewire\Shared;

use App\Contracts\SkillSyncGateway;
use Illuminate\Contracts\View\View;
use Livewire\Attributes\Locked;
use Livewire\Attributes\On;
use Livewire\Component;
use Symfony\Component\HttpKernel\Exception\HttpException;

class NotificationBell extends Component
{
    #[Locked]
    public ?int $unreadCount = null;

    public function mount(): void
    {
        $this->refreshCount();
    }

    #[On('notifications-updated')]
    public function refreshCount(): void
    {
        $this->unreadCount = null;
        if (! auth()->check()) {
            return;
        }

        try {
            $this->unreadCount = app(SkillSyncGateway::class)->unreadNotificationCount(auth()->user());
        } catch (HttpException $exception) {
            if ($exception->getStatusCode() < 500) {
                throw $exception;
            }
        }
    }

    public function render(): View
    {
        return view('livewire.shared.notification-bell');
    }
}
