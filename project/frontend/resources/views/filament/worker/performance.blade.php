<x-filament-panels::page class="ss-worker-performance">
    <div class="ss-alert"><x-filament::icon icon="heroicon-o-information-circle" /><div><strong>Your performance at a glance</strong><p>Your work history updates as you complete bookings and receive customer reviews.</p></div></div>
    <div class="ss-panel-columns">
        <section class="ss-card">
            <header class="ss-performance-heading">
                <span class="ss-eyebrow">YOUR SERVICES</span>
                <h2>Category performance</h2>
                <p class="ss-muted ss-performance-intro">Skill scores combine experience, completed jobs, and customer ratings.</p>
            </header>
            @forelse($performanceData['performance'] as $metric)
                <div class="ss-performance-row">
                    <div>
                        <h3>{{ $metric['category'] }}</h3>
                        <p class="ss-muted">{{ $metric['completedJobs'] }} {{ $metric['completedJobs'] == 1 ? 'completed job' : 'completed jobs' }}</p>
                    </div>
                    <x-score :value="$metric['skillScore']" label="Category skill score" />
                </div>
            @empty
                <div class="ss-empty"><h3>Not available yet</h3><p>Your categories do not have recorded work history yet.</p></div>
            @endforelse
        </section>
        <aside class="ss-card ss-performance-context">
            <header class="ss-performance-heading">
                <span class="ss-eyebrow">MODEL ESTIMATE</span>
                <h2>On-time completion</h2>
            </header>
            <x-score :value="$performanceData['reliabilityProbability']" :probability="true" label="Predicted on-time completion" />
            <p class="ss-muted">{{ $performanceData['reliabilityProbability'] === null ? 'An on-time completion estimate needs an available model and usable work-history inputs.' : 'The model estimates the chance of completing work by the agreed deadline. Missing history uses typical training values.' }}</p>
            <p class="ss-small ss-muted">On-time completion estimates, category skill, ratings, and recommendation rank describe different things. None is a guarantee.</p>
            @if($performanceData['reliabilityProbability'] !== null)
                <div class="ss-performance-notes"><x-prediction-context :data="$performanceData" /></div>
            @endif
        </aside>
    </div>
    <section class="ss-card"><div class="ss-section-heading"><h2>Your completed bookings</h2><span class="ss-muted">Your booking history</span></div>@forelse(collect($performanceData['bookings'])->where('status','completed') as $booking)<a class="ss-record-row" href="/worker/jobs/{{ $booking['id'] }}"><div class="ss-record-copy"><strong>{{ $booking['request']['title'] ?? 'Completed service' }}</strong><span>{{ $booking['request']['category'] ?? '' }} · {{ $this->localDate($booking['scheduledAt']) }}</span></div><x-status-badge status="completed" /></a>@empty<div class="ss-empty"><p>Completed bookings will appear here as you finish jobs.</p></div>@endforelse</section>
</x-filament-panels::page>

