@props(['status'])
<span {{ $attributes->class(['ss-status', 'ss-status-'.str_replace('_', '-', $status)]) }}>{{ ucfirst(str_replace('_', ' ', $status)) }}</span>
