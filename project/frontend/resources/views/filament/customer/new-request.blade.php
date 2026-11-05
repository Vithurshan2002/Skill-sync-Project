<x-filament-panels::page>
    <div class="ss-request-progress"><div class="ss-stepper" aria-label="Request progress"><span class="is-active" aria-current="step"><span class="ss-step-number">01</span><strong>Describe your job</strong></span><span><span class="ss-step-number">02</span><strong>Meet your matches</strong></span><span><span class="ss-step-number">03</span><strong>Make a booking</strong></span></div></div>
    <div class="ss-panel-columns">
        <section class="ss-card">
            @include('filament.shared.error')
            <form wire:submit="save" class="ss-form" x-data x-on:validation-error.window="$nextTick(() => $el.querySelector('[aria-invalid=true]')?.focus())">
                {{ $this->form }}
                <div class="ss-form-actions"><a class="ss-text-link" href="/customer/dashboard">Back to overview</a><x-filament::button type="submit" wire:loading.attr="disabled" wire:target="save" icon="heroicon-o-arrow-right" icon-position="after"><span wire:loading.remove wire:target="save">Save and continue</span><span wire:loading wire:target="save">Saving your request…</span></x-filament::button></div>
            </form>
        </section>
        <aside class="ss-card ss-request-help"><span class="ss-eyebrow">A LITTLE DETAIL HELPS</span><h2>Great matches start with a clear request.</h2><div class="ss-help-step"><span>01</span><p><strong>Tell us what’s happening</strong>Describe the issue and what you’d like done.</p></div><div class="ss-help-step"><span>02</span><p><strong>Choose a time that suits</strong>Your professional will confirm the appointment.</p></div><div class="ss-help-step"><span>03</span><p><strong>Explore your options</strong>Compare relevant skills and work history.</p></div></aside>
    </div>
</x-filament-panels::page>
