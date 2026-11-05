<x-filament-panels::page>
    <div class="ss-admin-dashboard">
        <section class="ss-card ss-admin-pending" wire:poll.30s>
            <div>
                <h2>Pending worker applications</h2>
                <p><strong>{{ $pendingApplications }}</strong> {{ $pendingApplications === 1 ? 'complete profile awaits' : 'complete profiles await' }} administrator review.</p>
            </div>
            <nav class="ss-admin-review-links" aria-label="Worker application actions">
                <a class="ss-text-link ss-admin-review-primary" href="/admin/records?entity=workers&amp;pendingOnly=1">Review pending applications</a>
                <a class="ss-text-link" href="/notifications">View notifications</a>
            </nav>
        </section>
        <section class="ss-card ss-admin-models">
            <div class="ss-admin-model-heading">
                <div>
                    <span class="ss-eyebrow">MATCHING AND MODELS</span>
                    <h2>Service matching and AI status</h2>
                </div>
                <div class="ss-icon-tile" aria-hidden="true"><x-filament::icon icon="heroicon-o-cpu-chip" /></div>
            </div>
            <p class="ss-muted">Workers are filtered by category, town, availability, and rate. AI estimates depend on model availability and recorded history.</p>
            <dl class="ss-admin-model-facts">
                @foreach(['classification' => 'Category classification', 'recommendations' => 'Recommendation ranking', 'performance' => 'Worker predictions'] as $key => $label)
                    <div><dt>{{ $label }}</dt><dd>{{ str_replace('_', ' ', ucfirst($models[$key] ?? 'unavailable')) }}</dd></div>
                @endforeach
            </dl>
        </section>
    <div class="ss-admin-grid">@foreach($counts as $entity => $count)<a class="ss-stat ss-admin-stat" href="/admin/records?entity={{ $entity }}"><span class="ss-muted">{{ ucfirst($entity) }}</span><strong>{{ $count }}</strong><span>Inspect records &rarr;</span></a>@endforeach</div>
    <div class="ss-panel-columns"><section class="ss-card"><span class="ss-eyebrow">YOUR WORKSPACE</span><h2>One view of every interaction.</h2><p class="ss-muted">View customer requests, worker profiles, booking progress, and reviews. Counts above reflect current records.</p><a class="ss-btn" href="/admin/records">Explore records &rarr;</a></section><aside class="ss-card ss-soft-card"><h3>Administration</h3><p class="ss-muted">Update category descriptions and record worker verification decisions. Every verification change requires a note. Booking rules apply to everyone.</p></aside></div>
        @if($evaluation)
            @if(isset($evaluation['trainingReadiness']))
                <section class="ss-card ss-admin-insight">
                    <div class="ss-admin-insight-heading">
                        <div>
                            <span class="ss-eyebrow">MODEL IMPROVEMENT</span>
                            <h2>Training data readiness</h2>
                            <p class="ss-muted">Track real booking outcomes collected for future model training.</p>
                        </div>
                        <span class="ss-admin-status">{{ $evaluation['trainingReadiness']['readyForSplitCheck'] ? 'Ready for split checks' : 'Collecting outcomes' }}</span>
                    </div>
                    <dl class="ss-admin-metrics">
                        @foreach(['rows' => 'Eligible outcomes', 'workers' => 'Workers', 'onTime' => 'On-time outcomes', 'late' => 'Late outcomes'] as $key => $label)
                            <div><dt>{{ $label }}</dt><dd>{{ $evaluation['trainingReadiness'][$key] }}</dd></div>
                        @endforeach
                    </dl>
                    <p class="ss-admin-insight-note">Minimum needed: <strong>{{ $evaluation['trainingReadiness']['minimumRows'] }} outcomes</strong>, <strong>{{ $evaluation['trainingReadiness']['minimumWorkers'] }} workers</strong>, and <strong>{{ $evaluation['trainingReadiness']['minimumPerClass'] }} outcomes each</strong> for on-time and late completion.</p>
                    <details class="ss-admin-disclosure">
                        <summary>Eligibility and training details</summary>
                        <div class="ss-admin-disclosure-content">
                            <p>Only bookings made after both participants enrolled as real users qualify. Demo and test activity is excluded.</p>
                            <p>Meeting these minimums allows chronological training split checks. It does not confirm model accuracy.</p>
                            <dl class="ss-admin-metadata">
                                <div><dt>Current model training contract</dt><dd>{{ ucfirst(str_replace('_', ' ', $models['trainingContract'] ?? 'unknown')) }}</dd></div>
                                <div><dt>Export feature version</dt><dd>{{ $evaluation['featureVersion'] }}</dd></div>
                            </dl>
                            <p>Retraining creates a separate candidate model. It does not automatically replace the active model.</p>
                        </div>
                    </details>
                </section>
            @endif
            <section class="ss-card ss-admin-insight">
                <div class="ss-admin-insight-heading">
                    <div>
                        <span class="ss-eyebrow">PREDICTION QUALITY</span>
                        <h2>On-time completion evaluation</h2>
                        <p class="ss-muted">Compare saved predictions with customer-confirmed job outcomes.</p>
                    </div>
                    <span class="ss-admin-status">{{ $evaluation['sampleCount'] }} eligible {{ $evaluation['sampleCount'] === 1 ? 'booking' : 'bookings' }}</span>
                </div>
                @if(!$evaluation['sampleCount'])
                    <div class="ss-admin-empty-state">
                        <h3>Waiting for confirmed outcomes</h3>
                        <p>Results appear when eligible bookings have a saved prediction and the customer confirms completion.</p>
                    </div>
                @endif
                @foreach($evaluation['models'] as $result)
                    <div class="ss-admin-model-result">
                        <h3>Model {{ substr($result['modelVersion'], 0, 12) }}</h3>
                        <dl class="ss-admin-metrics">
                            <div><dt>Evaluated bookings</dt><dd>{{ $result['sampleCount'] }}</dd></div>
                            <div><dt>Observed on-time rate</dt><dd>{{ number_format($result['onTimeRate'] * 100, 1) }}%</dd></div>
                            <div><dt>Accuracy at 50% threshold</dt><dd>{{ number_format($result['accuracyAtHalf'] * 100, 1) }}%</dd></div>
                            <div><dt>Brier score (lower is better)</dt><dd>{{ number_format($result['brierScore'], 4) }}</dd></div>
                        </dl>
                        <div class="ss-admin-table-scroll" role="region" aria-label="Prediction calibration for model {{ substr($result['modelVersion'], 0, 12) }}" tabindex="0">
                            <table>
                                <caption>Predictions compared with observed completion rates</caption>
                                <thead><tr><th scope="col">Prediction band</th><th scope="col">Bookings</th><th scope="col">Mean prediction</th><th scope="col">Observed on-time rate</th></tr></thead>
                                <tbody>
                                    @foreach($result['calibration'] as $band)
                                        <tr><td>{{ $band['lower'] * 100 }}&ndash;{{ $band['upper'] * 100 }}%</td><td>{{ $band['count'] }}</td><td>{{ $band['meanPrediction'] !== null ? number_format($band['meanPrediction'] * 100, 1).'%' : '?' }}</td><td>{{ $band['observedOnTimeRate'] !== null ? number_format($band['observedOnTimeRate'] * 100, 1).'%' : '?' }}</td></tr>
                                    @endforeach
                                </tbody>
                            </table>
                        </div>
                    </div>
                @endforeach
                <details class="ss-admin-disclosure">
                    <summary>Evaluation details and excluded records</summary>
                    <div class="ss-admin-disclosure-content">
                        <p><strong>Measured outcome:</strong> {{ $evaluation['target'] }}</p>
                        <p>{{ $evaluation['limitations'] }}</p>
                        <h3>Excluded records</h3>
                        <dl class="ss-admin-exclusions">
                            @forelse($evaluation['excluded'] as $reason => $count)
                                <div><dt>{{ ucfirst(preg_replace('/(?<!^)[A-Z]/', ' $0', $reason)) }}</dt><dd>{{ $count }}</dd></div>
                            @empty
                                <div><dt>Excluded records</dt><dd>None</dd></div>
                            @endforelse
                        </dl>
                    </div>
                </details>
            </section>
        @endif
    </div>
</x-filament-panels::page>
