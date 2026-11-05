@props(['data'])
@if(isset($data['dataSource']) && $data['dataSource'] !== 'real')
    <p class="ss-small ss-muted"><strong>{{ ucfirst($data['dataSource']) }} data.</strong> This estimate uses testing activity and is excluded from real-data evaluation and retraining.</p>
@endif
@if(($data['coldStart'] ?? false) || count($data['imputedFeatures'] ?? []))
    <p class="ss-small ss-muted"><strong>Limited work history.</strong> Some history is unavailable. The on-time completion model fills those values using typical values from its training data. Treat this estimate as provisional.</p>
@endif
@if(count($data['missingScoringFeatures'] ?? []))
    <p class="ss-small ss-muted">Skill and match scores use the available information. Unrecorded rating, certification, complaints, or distance are excluded from their calculation.</p>
@endif
