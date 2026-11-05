@props(['worker'])
@php
    $initials = collect(explode(' ', $worker['name']))->take(2)->map(fn ($part) => mb_substr($part, 0, 1))->join('');
@endphp
<article {{ $attributes->class(['ss-worker-card']) }}>
    @if(isset($worker['dataSource']) && $worker['dataSource'] !== 'real')<span class="ss-badge ss-worker-source">{{ ucfirst($worker['dataSource']) }} profile</span>@endif
    <div class="ss-worker-topline">
        <span class="ss-avatar ss-avatar-{{ (intval(substr($worker['id'], -2)) % 4) + 1 }}" aria-hidden="true">{{ $initials }}</span>
        <span class="ss-availability {{ $worker['available'] ? 'is-available' : '' }}"><span aria-hidden="true"></span>{{ $worker['available'] ? 'Available' : 'Unavailable' }}</span>
    </div>
    <div class="ss-worker-identity">
        <h3><a href="{{ route('workers.show', $worker['id']) }}">{{ $worker['name'] }}</a></h3>
        <p>{{ implode(' · ', $worker['categories']) }}</p>
    </div>
    <div class="ss-worker-meta"><span><x-icon name="heroicon-o-map-pin" />{{ $worker['town'] }}</span><span><x-icon name="heroicon-o-star" />@if($worker['rating'] !== null)<strong>{{ number_format($worker['rating'], 1) }}</strong> ({{ $worker['reviewCount'] }})@else No reviews yet @endif</span></div>
    <p class="ss-worker-bio">{{ $worker['bio'] }}</p>
    <div class="ss-worker-bottom"><div><strong>LKR {{ number_format($worker['rateLkr']) }}</strong><span> / {{ $worker['rateUnit'] }}</span></div><a href="{{ route('workers.show', $worker['id']) }}" class="ss-button ss-button-secondary ss-worker-profile-link">View profile <x-icon name="heroicon-o-arrow-up-right" /></a></div>
</article>
