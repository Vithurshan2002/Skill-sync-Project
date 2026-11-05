<x-filament-panels::page>
    <div class="ss-panel-columns {{ isset($workerReview) ? 'ss-worker-profile' : 'ss-customer-profile' }}">
        <section class="{{ isset($workerReview) ? 'ss-worker-profile-form' : 'ss-customer-profile-form' }}">
            @include('filament.shared.error')
            <form wire:submit="save" class="ss-form">
                {{ $this->form }}
                <div class="ss-form-actions {{ isset($workerReview) ? 'ss-profile-save-actions' : 'ss-customer-save-actions' }}">
                    @if(isset($workerReview))
                        <p class="ss-profile-save-status" role="status" aria-live="polite" aria-atomic="true">
                            {{ match($workerReview['approvalStatus'] ?? 'pending') {
                                'approved' => $profileSaved ? 'Profile saved.' : 'Profile approved.',
                                'changes_requested' => 'Changes requested. ' . (($workerReview['reviewNote'] ?? null) ?: 'Update your profile and save again.'),
                                default => ($workerReview['reviewReady'] ?? false) ? 'Request sent. Waiting for admin approval.' : 'Complete your profile and save to request approval.',
                            } }}
                        </p>
                    @else
                        <p class="ss-small ss-muted">Save your changes to update your account details.</p>
                    @endif
                    <x-filament::button type="submit" wire:loading.attr="disabled" wire:target="save">
                        <span wire:loading.remove wire:target="save">Save profile</span>
                        <span wire:loading wire:target="save">Saving&hellip;</span>
                    </x-filament::button>
                </div>
            </form>
        </section>
        @if(isset($workerReview))
        <aside class="ss-card ss-worker-profile-guide" aria-labelledby="profile-guide-title">
            <div class="ss-worker-profile-identity">
                <div class="ss-avatar" aria-hidden="true">{{ collect(explode(' ', auth()->user()->name))->filter()->take(2)->map(fn($part) => mb_substr($part, 0, 1))->join('') }}</div>
                <div><h2>{{ auth()->user()->name }}</h2><span>Worker profile</span></div>
            </div>
            <h3 id="profile-guide-title">Help customers choose you</h3>
            <p>A clear profile helps customers understand what you offer.</p>
            <ul class="ss-worker-profile-tips">
                <li><x-icon name="heroicon-o-pencil-square" /><div><strong>Describe your skills</strong><p>Mention the jobs you handle and your experience.</p></div></li>
                <li><x-icon name="heroicon-o-map-pin" /><div><strong>Check your service area</strong><p>Keep your towns and travel radius up to date.</p></div></li>
                <li><x-icon name="heroicon-o-calendar-days" /><div><strong>Keep availability current</strong><p>Let customers know when you can take new jobs.</p></div></li>
            </ul>
            @if($workerReview['verified'] ?? false)
                <a class="ss-button ss-button-secondary" href="/workers/{{ auth()->user()->worker_id }}">Preview public profile <x-icon name="heroicon-o-arrow-up-right" /></a>
            @endif
        </aside>
        @else
        <aside class="ss-card ss-customer-profile-guide" aria-labelledby="customer-profile-guide-title">
            <div class="ss-customer-profile-identity">
                <div class="ss-avatar" aria-hidden="true">{{ collect(explode(' ', auth()->user()->name))->filter()->take(2)->map(fn($part) => mb_substr($part, 0, 1))->join('') }}</div>
                <div><h2>{{ auth()->user()->name }}</h2><span>Customer account</span></div>
            </div>
            <h3 id="customer-profile-guide-title">Make booking coordination easier</h3>
            <p>Accurate contact details help professionals coordinate the work with you.</p>
            <ul class="ss-customer-profile-tips">
                <li><x-icon name="heroicon-o-phone" /><div><strong>Add a reachable phone number</strong><p>It gives your professional another way to coordinate the job.</p></div></li>
                <li><x-icon name="heroicon-o-chat-bubble-left-right" /><div><strong>Choose how to be contacted</strong><p>Your preference helps set expectations before a booking.</p></div></li>
                <li><x-icon name="heroicon-o-map-pin" /><div><strong>Keep your town current</strong><p>Your town can help with local service requests.</p></div></li>
            </ul>
        </aside>
        @endif
    </div>
</x-filament-panels::page>
