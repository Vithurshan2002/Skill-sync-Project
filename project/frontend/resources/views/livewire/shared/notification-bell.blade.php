<div class="ss-notification-bell" wire:poll.30s="refreshCount">
    <a class="ss-icon-button" href="{{ \App\Filament\Shared\NotificationsPage::getUrl(panel: auth()->user()->role) }}"
        aria-label="{{ $unreadCount === null ? 'Notifications (unread count unavailable)' : 'Notifications, ' . $unreadCount . ' unread' }}"
        title="{{ $unreadCount === null ? 'Notifications (unread count unavailable)' : $unreadCount . ' unread notifications' }}">
        <x-filament::icon icon="heroicon-o-bell" />
        @if($unreadCount > 0)
            <span class="ss-notification-count" aria-hidden="true">{{ $unreadCount > 99 ? '99+' : $unreadCount }}</span>
        @endif
    </a>
    <span class="sr-only" role="status" aria-live="polite" aria-atomic="true">{{ $unreadCount === null ? 'Unread notification count unavailable.' : $unreadCount . ' unread notifications.' }}</span>
</div>
