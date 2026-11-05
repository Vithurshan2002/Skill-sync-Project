@props(['name' => 'heroicon-o-squares-2x2'])
<x-dynamic-component :component="$name" {{ $attributes->merge(['class' => 'ss-icon']) }} aria-hidden="true" />
