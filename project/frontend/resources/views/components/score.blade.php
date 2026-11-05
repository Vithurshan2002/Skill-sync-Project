@props(['value' => null, 'label' => 'Category skill score', 'probability' => false])
<div {{ $attributes->class(['ss-score']) }}>
    <span class="ss-score-label">{{ $label }}</span>
    @if($value === null)
        <span class="ss-score-missing">Not available yet</span>
    @else
        @php($number = $probability ? round($value * 100) : round($value))
        <strong>{{ $number }}<span>{{ $probability ? '%' : '/100' }}</span></strong>
        <div class="ss-score-track" aria-hidden="true"><span style="width: {{ max(0, min(100, $number)) }}%"></span></div>
    @endif
</div>
