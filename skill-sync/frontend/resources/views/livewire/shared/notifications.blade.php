<section class="ss-workspace-notifications" aria-label="Your notifications" wire:poll.30s>
    <div class="ss-filter-tabs" aria-label="Filter notifications"><button wire:click="$set('filter', 'all')" @class(['is-active' => $filter === 'all'])>All notifications</button><button wire:click="$set('filter', 'unread')" @class(['is-active' => $filter === 'unread'])>Unread <span>{{ $unread }}</span></button></div>
    @if($readError)<p class="ss-alert" role="alert">{{ $readError }}</p>@endif
    <p class="ss-loading-feedback" wire:loading.delay wire:target="filter" role="status">Loading notifications…</p>
    <div class="ss-card ss-notification-list">
        @forelse($items as $item)
            <article @class(['ss-notification', 'is-unread' => !$item['readAt']]) wire:key="{{ $item['id'] }}">
                <span class="ss-notification-icon"><x-filament::icon icon="heroicon-o-bell" /></span>
                <div class="ss-notification-copy">
                    @if(!$item['readAt'])<span class="sr-only">Unread notification</span>@endif
                    <a href="{{ $item['targetPath'] }}" wire:click.prevent="openNotification('{{ $item['id'] }}')">{{ $item['message'] }}</a>
                    <span class="ss-loading-feedback" wire:loading wire:target="openNotification('{{ $item['id'] }}')" role="status">Opening…</span>
                    <p class="ss-muted">{{ \Carbon\Carbon::parse($item['createdAt'])->timezone('Asia/Colombo')->format('d M Y, g:i a') }} · Sri Lanka time</p>
                </div>
                @if(!$item['readAt'])
                    <button class="ss-text-button" wire:click="markRead('{{ $item['id'] }}')" wire:loading.attr="disabled" wire:target="markRead('{{ $item['id'] }}')"><span wire:loading.remove wire:target="markRead('{{ $item['id'] }}')">Mark read</span><span wire:loading wire:target="markRead('{{ $item['id'] }}')" role="status">Marking read…</span></button>
                @else
                    <span class="ss-notification-read">Read</span>
                @endif
            </article>
        @empty
            <div class="ss-empty"><x-filament::icon icon="heroicon-o-bell-slash" /><h2>You're all caught up</h2><p>New booking activity will appear here.</p><a class="ss-button ss-button-secondary" href="/{{ auth()->user()->role }}/dashboard">Back to workspace</a></div>
        @endforelse
    </div>
</section>
