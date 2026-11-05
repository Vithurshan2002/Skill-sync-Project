<div>
    <section class="ss-page-heading ss-container"><span class="ss-eyebrow">SKILLS THAT FIT YOUR PLANS</span><h1>Find your next<br><em>helping hand.</em></h1><p>Explore local specialists by skill, location, and availability.</p></section>
    <section class="ss-container ss-section ss-section-tight">
        <form class="ss-directory-filters" wire:submit.prevent="$refresh">
            <div class="ss-field"><label for="worker-search">Search specialists</label><div class="ss-input-icon"><x-icon name="heroicon-o-magnifying-glass" /><input id="worker-search" class="ss-input" type="search" wire:model.live.debounce.350ms="search" placeholder="Name or skill"></div></div>
            <div class="ss-field"><label for="worker-category">Service category</label><div class="ss-filter-select"><select id="worker-category" class="ss-input" wire:model.live="category"><option value="">All services</option>@foreach($categories as $item)<option value="{{ $item['label'] }}">{{ $item['label'] }}</option>@endforeach</select><x-icon name="heroicon-o-chevron-down" /></div></div>
            <div class="ss-field"><label for="worker-town">Town</label><div class="ss-filter-select"><select id="worker-town" class="ss-input" wire:model.live="town"><option value="">All towns</option>@foreach(['Colombo', 'Galle', 'Jaffna', 'Kandy'] as $place)<option value="{{ $place }}">{{ $place }}</option>@endforeach</select><x-icon name="heroicon-o-chevron-down" /></div></div>
            <label class="ss-checkbox"><input type="checkbox" wire:model.live="available">Available only</label>
            <button class="ss-text-link" type="button" wire:click="clearFilters" wire:loading.attr="disabled">Clear filters</button>
        </form>
        <div class="ss-results-heading"><p><strong>{{ $meta['total'] }}</strong> {{ $meta['total'] === 1 ? 'specialist' : 'specialists' }}{{ $category ? ' for '.$category : '' }}{{ $town ? ' in '.$town : '' }}</p><span wire:loading role="status" class="ss-loading-feedback">Finding specialists…</span><span wire:loading.remove class="ss-muted">Registered professionals</span></div>
        @if($error)
            <div class="ss-empty" role="alert"><x-icon name="heroicon-o-exclamation-circle" /><h2>Let's try that again.</h2><p>{{ $error }}</p><button wire:click="$refresh" wire:loading.attr="disabled" class="ss-button ss-button-primary">Retry directory</button></div>
        @elseif(count($workers) === 0)
            <div class="ss-empty"><x-icon name="heroicon-o-magnifying-glass" /><h2>No suitable workers found</h2><p>Try another town or service, or include unavailable specialists.</p><button wire:click="clearFilters" wire:loading.attr="disabled" class="ss-button ss-button-primary">Clear all filters</button></div>
        @else
            <div class="ss-worker-grid" wire:loading.class="ss-loading">@foreach($workers as $worker)<x-worker-card :worker="$worker" wire:key="worker-{{ $worker['id'] }}" />@endforeach</div>
        @endif
        @if($meta['total'] > $meta['perPage'])
            <nav class="ss-pagination" aria-label="Worker directory pagination"><button class="ss-button ss-button-secondary" wire:loading.attr="disabled" wire:click="setPage({{ max(1, $page - 1) }})" @disabled($page <= 1)><x-icon name="heroicon-o-arrow-left" /> Previous</button><span>Page {{ $page }} of {{ (int) ceil($meta['total'] / $meta['perPage']) }}</span><button class="ss-button ss-button-secondary" wire:loading.attr="disabled" wire:click="setPage({{ $page + 1 }})" @disabled($page * $meta['perPage'] >= $meta['total'])>Next <x-icon name="heroicon-o-arrow-right" /></button></nav>
        @endif
        <p class="ss-section-note"><x-icon name="heroicon-o-information-circle" />Compare services, availability, rates, and customer feedback.</p>
    </section>
</div>
