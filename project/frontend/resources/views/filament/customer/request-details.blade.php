<x-filament-panels::page>
    @include('filament.shared.error')
    <x-back-link href="/customer/dashboard">Back to your requests</x-back-link>
    @if($requestRecord['status'] === 'submitted')
        <div>{{ $this->editAction }}</div>
    @endif
    <section class="ss-card ss-location-summary">
        <div><h2>Job location</h2><p>{{ isset($requestRecord['latitude'], $requestRecord['longitude']) ? 'GPS location saved. Nearby matches use worker travel radii.' : 'Town matching is active. Add a job location to compare GPS distances.' }}</p></div>
    </section>
    <div class="ss-panel-columns">
        <section class="ss-card"><div class="ss-section-heading"><span class="ss-eyebrow">REQUEST {{ $requestRecord['id'] }}</span><x-status-badge :status="$requestRecord['status']" /></div><h2>{{ $requestRecord['title'] }}</h2><p class="ss-description">{{ $requestRecord['description'] }}</p><dl class="ss-detail-grid"><div><dt>Location</dt><dd>{{ $requestRecord['town'] }}</dd></div><div><dt>Preferred time</dt><dd>{{ $this->localDate($requestRecord['preferredAt']) }}</dd></div><div><dt>Category</dt><dd>{{ $requestRecord['category'] ?? 'Ready to find out' }}</dd></div><div><dt>Budget</dt><dd>{{ isset($requestRecord['budgetLkr']) ? 'LKR '.number_format($requestRecord['budgetLkr']) : 'Open to discussion' }}</dd></div>@if($requestRecord['address'] ?? null)<div><dt>Address</dt><dd>{{ $requestRecord['address'] }}</dd></div>@endif</dl></section>
        <aside class="ss-card ss-soft-card"><span class="ss-eyebrow">YOUR NEXT STEP</span><h2>Let’s find your professional.</h2><p class="ss-muted">See who offers the skills you need near your job location, with clear reasons for each suggestion.</p>
            @if(in_array($requestRecord['status'], ['booked', 'closed']))<a class="ss-btn" href="/customer/bookings">View your booking →</a>@else<x-filament::button wire:click="findWorkers" wire:loading.attr="disabled" icon="heroicon-o-sparkles"><span wire:loading.remove wire:target="findWorkers">Find suitable workers</span><span wire:loading wire:target="findWorkers">Finding matching workers…</span></x-filament::button>@endif
            <p class="ss-small ss-muted">Choose a service category to find workers who cover your location.</p>
        </aside>
    </div>
</x-filament-panels::page>
