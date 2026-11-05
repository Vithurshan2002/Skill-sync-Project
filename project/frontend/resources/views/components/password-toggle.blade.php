@props(['target', 'label' => 'password'])

<button type="button" class="ss-password-toggle" data-password-toggle data-password-label="{{ $label }}" aria-controls="{{ $target }}" aria-label="Show {{ $label }}" hidden>
    <span data-password-hidden-icon><x-icon name="heroicon-o-eye-slash" /></span>
    <span data-password-visible-icon hidden><x-icon name="heroicon-o-eye" /></span>
</button>
