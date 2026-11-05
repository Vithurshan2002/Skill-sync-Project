<x-filament-panels::page>
    <div class="ss-tabs" aria-label="Filter bookings by status">
        @foreach(['' => 'All jobs', 'pending' => 'Pending', 'accepted' => 'Accepted', 'in_progress' => 'In progress', 'awaiting_confirmation' => 'Awaiting confirmation', 'completed' => 'Completed', 'rejected' => 'Rejected', 'cancelled' => 'Cancelled'] as $value => $label)
            <button type="button" @class(['ss-tab', 'is-active' => $status === $value]) wire:click="$set('status', '{{ $value }}')" aria-pressed="{{ $status === $value ? 'true' : 'false' }}">{{ $label }}</button>
        @endforeach
    </div>
    <div wire:loading.flex wire:target="status" class="ss-loading-feedback" role="status">Updating your jobs…</div>
    <section class="ss-card ss-bookings-list"><div class="ss-section-heading"><h2>{{ $status ? str_replace('_', ' ', ucfirst($status)) : 'All' }} bookings</h2><span class="ss-muted">{{ count($bookings) }} {{ count($bookings) === 1 ? 'job' : 'jobs' }}</span></div>
        @forelse(collect($bookings)->sortByDesc('scheduledAt') as $booking)
            <a class="ss-record-row" href="/{{ $area }}/{{ $recordPath }}/{{ $booking['id'] }}" wire:key="booking-{{ $booking['id'] }}"><div class="ss-icon-tile"><x-filament::icon icon="heroicon-o-wrench-screwdriver" /></div><div class="ss-record-copy"><strong>{{ $booking['request']['title'] ?? 'Service booking' }}</strong><span>{{ $area === 'customer' ? ($booking['worker']['name'] ?? '') : ($booking['request']['town'] ?? '') }} · {{ $this->localDate($booking['scheduledAt']) }}</span></div><div class="ss-record-price">LKR {{ number_format($booking['quotedRateLkr']) }}<span>/ {{ $booking['rateUnit'] }}</span></div><x-status-badge :status="$booking['status']" /><span aria-hidden="true">↗</span></a>
        @empty
            <div class="ss-empty"><x-filament::icon icon="heroicon-o-calendar-days" /><h3>No {{ str_replace('_',' ', $status) }} bookings yet.</h3><p>{{ $area === 'customer' ? 'Your next great professional is a request away.' : 'New opportunities will appear here when customers book your services.' }}</p>@if($area === 'customer')<a class="ss-btn" href="/customer/requests/new">Create a request</a>@endif</div>
        @endforelse
    </section>
</x-filament-panels::page>
