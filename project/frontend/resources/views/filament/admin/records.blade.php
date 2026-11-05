<x-filament-panels::page>
    <div style="display: contents" x-data="{ listScroll: 0 }"
         x-init="$watch('$wire.recordId', value => $nextTick(() => requestAnimationFrame(() => window.scrollTo({ top: value ? 0 : listScroll, behavior: 'instant' }))))">
    @include('filament.shared.error')
    <p class="ss-loading-feedback" wire:loading.delay wire:target="entity,recordId,detailTab,search,pendingOnly" role="status">Loading records…</p>
    @if(!$selected)
    @if($entity === 'workers')
        <label class="ss-record-approval-filter">
            <input type="checkbox" wire:model.live="pendingOnly">
            <span>Ready for approval only</span>
        </label>
    @endif
    <div class="ss-tabs" aria-label="Record types">@foreach(['workers','customers','categories','requests','bookings','reviews','complaints'] as $type)<button type="button" @class(['ss-tab', 'is-active' => $entity === $type]) wire:click="$set('entity', '{{ $type }}')" aria-pressed="{{ $entity === $type ? 'true' : 'false' }}">{{ ucfirst($type) }}</button>@endforeach</div>
    @endif
    @if($selected)
        <x-back-link wire:click="$set('recordId', '')">Back to records</x-back-link>
        @if($entity === 'workers')
            <section class="ss-card ss-worker-record" aria-label="Worker record">
                <header class="ss-worker-record-header">
                    <div>
                        <p class="ss-record-kicker">Worker profile</p>
                        <h2>{{ $selected['name'] }}</h2>
                        <p class="ss-record-id">Worker ID <span>{{ $selected['id'] }}</span></p>
                    </div>
                    <div class="ss-record-header-actions">
                        <span class="ss-review-status" data-status="{{ $selected['approvalStatus'] ?? 'pending' }}">{{ ucfirst(str_replace('_', ' ', $selected['approvalStatus'] ?? 'pending')) }}</span>
                    </div>
                </header>
                @if(!($selected['reviewReady'] ?? true))
                    @php
                        $missingProfileFields = [];
                        if (mb_strlen(trim($selected['bio'] ?? '')) < 15) { $missingProfileFields[] = 'biography (at least 15 characters)'; }
                        if (empty($selected['categories'])) { $missingProfileFields[] = 'service categories'; }
                        if (empty($selected['serviceTowns'])) { $missingProfileFields[] = 'service towns'; }
                        if (empty($selected['rateLkr'])) { $missingProfileFields[] = 'service rate'; }
                    @endphp
                    <div class="ss-review-feedback" role="status">
                        <strong>Profile incomplete</strong>
                        <p>Before approval, the worker must add: {{ implode(', ', $missingProfileFields) ?: 'the required profile details' }}. You can use Review application to request these changes.</p>
                    </div>
                @endif
                <div class="ss-tabs ss-record-tabs" aria-label="Worker record sections">
                    <button type="button" @class(['ss-tab', 'is-active' => $detailTab === 'profile']) wire:click="$set('detailTab', 'profile')" aria-pressed="{{ $detailTab === 'profile' ? 'true' : 'false' }}">Profile details</button>
                    <button type="button" @class(['ss-tab', 'is-active' => $detailTab === 'changes']) wire:click="$set('detailTab', 'changes')" aria-pressed="{{ $detailTab === 'changes' ? 'true' : 'false' }}">Change requests</button>
                </div>
                @if($detailTab === 'changes')
                    <section class="ss-record-panel" aria-label="Profile changes">
                        <div class="ss-record-section-heading">
                            <h3>Changes awaiting review</h3>
                            <p>Compare the previous details with the worker's latest updates.</p>
                        </div>
                        @if($selected['reviewNote'] ?? null)
                            <div class="ss-review-feedback"><strong>Admin feedback</strong><p>{{ $selected['reviewNote'] }}</p></div>
                        @endif
                        <div class="ss-change-list">
                            @forelse($selected['profileChanges'] ?? [] as $change)
                                <section class="ss-change-row" aria-label="{{ $change['label'] }} change">
                                    <h4>{{ $change['label'] }}</h4>
                                    <dl class="ss-change-values">
                                        @foreach(['before' => 'Previous value', 'after' => 'New value'] as $side => $label)
                                            <div class="ss-change-value ss-change-value-{{ $side }}">
                                                <dt>{{ $label }}</dt>
                                                <dd>{{ is_array($change[$side]) ? (implode(', ', $change[$side]) ?: 'Not set') : (($change[$side] === null || $change[$side] === '') ? 'Not set' : $change[$side]) }}@if($change['field'] === 'yearsExperience') {{ $change[$side] == 1 ? 'year' : 'years' }}@endif</dd>
                                            </div>
                                        @endforeach
                                    </dl>
                                </section>
                            @empty
                                <div class="ss-record-empty"><h4>No recorded changes</h4><p>Use Profile details to review this worker. Changes made before tracking began are not available here.</p></div>
                            @endforelse
                        </div>
                        <footer class="ss-record-action-bar">
                            <p>Review the updated details and approve them or request corrections.</p>
                            {{ ($this->reviewChangesAction)(['id' => $selected['id']]) }}
                        </footer>
                    </section>
                @else
                    <section class="ss-record-panel" aria-label="Profile details">
                        <section class="ss-record-profile-section">
                            <h3>About the worker</h3>
                            <p class="ss-worker-description">{{ $selected['bio'] ?: 'No biography provided.' }}</p>
                        </section>
                        <section class="ss-record-profile-section">
                            <h3>Work details</h3>
                            <dl class="ss-worker-facts">
                                <div><dt>Home town</dt><dd>{{ $selected['town'] }}</dd></div>
                                <div><dt>Experience</dt><dd>{{ $selected['yearsExperience'] }} {{ $selected['yearsExperience'] == 1 ? 'year' : 'years' }}</dd></div>
                                <div><dt>Service rate</dt><dd>{{ $selected['rateLkr'] !== null ? 'LKR '.number_format($selected['rateLkr'], 2) : 'Not set' }}@if($selected['rateLkr'] !== null)<span class="ss-value-unit"> / {{ $selected['rateUnit'] }}</span>@endif</dd></div>
                                <div><dt>Service location (private)</dt><dd>{{ isset($selected['latitude'], $selected['longitude']) ? $selected['latitude'].', '.$selected['longitude'] : 'Not set; town matching' }}</dd></div>
                                <div><dt>Service radius</dt><dd>{{ isset($selected['serviceRadiusKm']) ? $selected['serviceRadiusKm'].' km' : 'Not set' }}</dd></div>
                                <div><dt>Availability</dt><dd>{{ $selected['available'] ? 'Available for new jobs' : 'Unavailable for new jobs' }}</dd></div>
                                <div><dt>Service categories</dt><dd class="ss-record-tags">@forelse($selected['categories'] as $category)<span>{{ $category }}</span>@empty<span>Not set</span>@endforelse</dd></div>
                                <div><dt>Service towns</dt><dd class="ss-record-tags">@forelse($selected['serviceTowns'] as $town)<span>{{ $town }}</span>@empty<span>Not set</span>@endforelse</dd></div>
                            </dl>
                        </section>
                        <section class="ss-record-profile-section">
                            <div class="ss-record-section-heading"><h3>Recorded performance</h3><p>Scores and ratings use the available booking history.</p></div>
                            <dl class="ss-worker-facts">
                                <div><dt>Customer rating</dt><dd>{{ $selected['rating'] !== null ? number_format($selected['rating'], 2).' / 5' : 'No rated jobs yet' }}<span class="ss-value-note">{{ $selected['reviewCount'] }} {{ $selected['reviewCount'] == 1 ? 'review' : 'reviews' }}</span></dd></div>
                                <div><dt>Predicted on-time completion</dt><dd>{{ $selected['reliabilityProbability'] !== null ? number_format($selected['reliabilityProbability'] * 100, 1).'%' : 'No estimate available' }}</dd></div>
                            </dl>
                            @if(count($selected['performance'] ?? []))
                                <div class="ss-category-performance">
                                    @foreach($selected['performance'] as $metric)
                                        <div class="ss-category-performance-row"><div><strong>{{ $metric['category'] }}</strong><span>{{ $metric['completedJobs'] }} {{ $metric['completedJobs'] == 1 ? 'completed job' : 'completed jobs' }}</span></div><div><span>Category skill score</span><strong>{{ $metric['skillScore'] !== null ? number_format($metric['skillScore'], 0).' / 100' : 'No score available' }}</strong></div></div>
                                    @endforeach
                                </div>
                            @endif
                        </section>
                        <section class="ss-record-profile-section ss-record-admin">
                            <div><h3>Administration</h3><p>Data source: <strong>{{ ucfirst($selected['dataSource'] ?? 'test') }}</strong></p><p class="ss-record-help">@if(($selected['dataSource'] ?? '') === 'demo')Demo accounts cannot become Real or Test. Register a separate genuine account for real activity.@else Source changes apply to future bookings.@endif</p></div>
                            <div class="ss-record-admin-actions">{{ ($this->dataSourceAction)(['id' => $selected['id']]) }}@if($selected['verified'] ?? false)<a class="ss-text-link" href="/workers/{{ $selected['id'] }}">View public profile</a>@endif</div>
                        </section>
                        <footer class="ss-record-action-bar">
                            <p>Review the worker's profile and approve the application or request corrections.</p>
                            {{ ($this->verifyAction)(['id' => $selected['id']]) }}
                        </footer>
                    </section>
                @endif
            </section>
        @else
        <section class="ss-card"><div class="ss-section-heading"><div><span class="ss-eyebrow">{{ strtoupper(rtrim($entity,'s')) }} {{ $selected['id'] }}</span><h2>{{ $selected['name'] ?? $selected['label'] ?? $selected['title'] ?? 'Record details' }}</h2></div></div>
            <section aria-label="Profile details">
            <dl class="ss-detail-grid">
@foreach($selected as $key => $value)@if(!is_array($value) && !($entity === 'customers' && $key === 'workerId'))<div><dt>{{ ucfirst(preg_replace('/(?<!^)[A-Z]/', ' $0', $key)) }}</dt><dd>@if(is_bool($value)){{ $value ? 'Yes' : 'No' }}

@elseif($value === null)Not available / insufficient history

@elseif(in_array($key, ['createdAt','scheduledAt','scheduledEndAt','deadlineAt','preferredAt'])){{ $this->localDate($value) }}
@else{{ $value }}
@endif</dd></div>
@endif @endforeach</dl>
            @foreach(['categories' => 'Service categories', 'serviceTowns' => 'Service towns'] as $key => $label)@if(isset($selected[$key]))<p><strong>{{ $label }}:</strong> {{ implode(', ', $selected[$key]) }}</p>
@endif @endforeach
            @if(isset($selected['performance']))<div class="ss-score-grid">@foreach($selected['performance'] as $metric)<div><x-score :value="$metric['skillScore']" :label="$metric['category'].' · Category skill score'" /><p class="ss-muted">{{ $metric['completedJobs'] }} completed jobs</p></div>@endforeach</div>
@endif
            @if(isset($selected['history']))<ol class="ss-timeline">@foreach($selected['history'] as $event)<li><span class="ss-timeline-dot" aria-hidden="true"></span><div><x-status-badge :status="$event['status']" /><time>{{ $this->localDate($event['at']) }}</time>@if($event['note'] ?? null)<p>{{ $event['note'] }}</p>
@endif</div></li>@endforeach</ol>
@endif
            @if($entity === 'complaints' && $selected['status'] === 'pending'){{ ($this->resolveComplaintAction)(['id' => $selected['id']]) }}@endif
            @if(in_array($entity, ['workers', 'customers']))<div class="ss-form-actions">{{ ($this->dataSourceAction)(['id' => $selected['id']]) }}</div>@endif
            @if($entity === 'categories')<div class="ss-form-actions">{{ ($this->editCategoryAction)(['id' => $selected['id']]) }}</div>
@endif
            @if($entity === 'workers')<div class="ss-form-actions">@if($selected['verified'] ?? false)<a class="ss-text-link" href="/workers/{{ $selected['id'] }}">Public profile ↗</a>@endif</div><p class="ss-small ss-muted">Only approved, complete profiles appear in search and recommendations or receive new bookings. Decisions are audited and sent to the worker. Existing bookings remain accessible.</p>
@endif
            </section>
        </section>
        @endif
    @endif
    @if(!$selected)
    <section class="ss-card" x-on:click.capture="listScroll = window.scrollY"><div class="ss-section-heading ss-record-list-heading"><h2 class="ss-record-list-title"><span>{{ ucfirst($entity) }}</span><span class="ss-record-count">{{ count($records) }}</span></h2><label class="ss-field"><span class="sr-only">Search records</span><input type="search" wire:model.live.debounce.300ms="search" placeholder="Search {{ $entity }}…"></label></div>
        {{ $this->table }}
    </section>
    @endif
    </div>
</x-filament-panels::page>
