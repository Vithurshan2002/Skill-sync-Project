@props(['href' => null])
@if($href)
    <a href="{{ $href }}" {{ $attributes->class(['ss-return-link']) }}><x-icon name="heroicon-o-arrow-left" /><span>{{ $slot }}</span></a>
@else
    <button type="button" {{ $attributes->class(['ss-return-link']) }}><x-icon name="heroicon-o-arrow-left" /><span>{{ $slot }}</span></button>
@endif
