<x-filament-panels::page>
    <div class="ss-panel-welcome"><span class="ss-eyebrow">YOUR SPACE</span><p>Welcome back, {{ explode(' ', auth()->user()->name)[0] }} <span aria-hidden="true">✦</span></p></div>
    <div class="ss-panel-columns">
        <section class="ss-card">
            <div class="ss-section-heading"><div><span class="ss-eyebrow">WHAT’S NEXT</span><h2>Your upcoming work</h2></div><a class="ss-text-link" href="/customer/bookings">All bookings →</a></div>
            @forelse(collect($bookings)->whereIn('status', ['pending','accepted','in_progress','awaiting_confirmation'])->sortBy('scheduledAt')->take(4) as $booking)
                <a class="ss-record-row" href="/customer/bookings/{{ $booking['id'] }}">
                    <div class="ss-icon-tile"><x-filament::icon icon="heroicon-o-calendar-days" /></div>
                    <div class="ss-record-copy"><strong>{{ $booking['request']['title'] ?? 'Service booking' }}</strong><span>{{ $booking['worker']['name'] ?? 'Your professional' }} · {{ $this->localDate($booking['scheduledAt']) }}</span></div>
                    <x-status-badge :status="$booking['status']" />
                </a>
            @empty
                <div class="ss-empty"><h3>A little breathing room.</h3><p>You don’t have any upcoming work. Create a request whenever you need a hand.</p><a class="ss-btn" href="/customer/requests/new">Create a request</a></div>
            @endforelse
        </section>
        <aside class="ss-card ss-soft-card ss-customer-start-card">
            <span class="ss-eyebrow">A GOOD PLACE TO START</span>
            <h2>Small fix. Big difference.</h2>
            <p class="ss-muted">A leaking tap, a stubborn fan, or a room ready for a fresh coat. Tell us what needs doing.</p>
            <a class="ss-btn" href="/customer/requests/new">Find the right skills <span aria-hidden="true">↗</span></a>
            <p class="ss-small ss-muted">Local professionals. Clear work history.</p>
        </aside>
    </div>
    <section class="ss-card"><div class="ss-section-heading"><h2>Your requests</h2><span class="ss-muted">{{ count($requests) }} requests</span></div>
        @forelse(collect($requests)->reverse() as $request)
            <a class="ss-record-row" href="/customer/requests/{{ $request['id'] }}"><div class="ss-record-copy"><strong>{{ $request['title'] }}</strong><span>{{ $request['category'] ?? 'Category to be selected' }} · {{ $request['town'] }}</span></div><x-status-badge :status="$request['status']" /><span aria-hidden="true">↗</span></a>
        @empty <div class="ss-empty"><p>Your first request is one small step away.</p></div> @endforelse
    </section>
    @if(count($notifications))
        <section class="ss-card"><div class="ss-section-heading"><h2>Recent updates</h2><a class="ss-text-link" href="/notifications">View all →</a></div>@foreach(collect($notifications)->reverse()->take(3) as $notification)<a class="ss-record-row" href="{{ $notification['targetPath'] }}"><x-filament::icon icon="heroicon-o-bell" /><div class="ss-record-copy"><strong>{{ $notification['message'] }}</strong><span>{{ $this->localDate($notification['createdAt']) }}</span></div></a>@endforeach</section>
    @endif
</x-filament-panels::page>
