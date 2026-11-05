@props(['data', 'model' => false])
@php
    $reasons = array_values($data['reasons'] ?? []);
    $limitedHistory = ($data['coldStart'] ?? false) || count($data['imputedFeatures'] ?? []);
    $dataSource = $data['dataSource'] ?? 'real';
@endphp
@if($model && ($data['reliabilityProbability'] ?? null) !== null && $limitedHistory)
    <p class="ss-estimate-note"><x-filament::icon icon="heroicon-o-information-circle" /><span><strong>Provisional estimate</strong> — limited work history.</span></p>
@endif
@if($dataSource !== 'real')
    <p class="ss-estimate-note"><x-filament::icon icon="heroicon-o-beaker" /><span><strong>{{ ucfirst($dataSource) }} data</strong> — based on testing activity.</span></p>
@endif
<div class="ss-explanation">
    <h4>Why this professional?</h4>
    @if(count($reasons))
        <ul class="ss-reason-list ss-reason-preview">
            @foreach(array_slice($reasons, 0, 3) as $reason)
                <li><x-filament::icon icon="heroicon-o-check" /><span>{{ $reason }}</span></li>
            @endforeach
        </ul>
    @else
        <p>No recommendation reasons are available yet.</p>
    @endif
    <details class="ss-match-details">
        <summary>{{ count($reasons) > 3 ? 'More reasons and how this score works' : 'How this score works' }}</summary>
        @if(count($reasons) > 3)
            <ul class="ss-reason-list ss-reason-more">
                @foreach(array_slice($reasons, 3) as $reason)
                    <li><span>{{ $reason }}</span></li>
                @endforeach
            </ul>
        @endif
        <p>Match score: {{ ($data['matchScore'] ?? null) === null ? 'Not available yet' : $data['matchScore'].'/100' }}</p>
        <p>Category skill scores use a weighted formula. Predicted on-time completion is a model estimate.</p>
        @if($model && $limitedHistory)
            <p>Missing work-history inputs use typical values from the model's training data.</p>
        @endif
        @if(count($data['missingScoringFeatures'] ?? []))
            <p>Unrecorded information is excluded from the skill and match score calculations.</p>
        @endif
    </details>
</div>
