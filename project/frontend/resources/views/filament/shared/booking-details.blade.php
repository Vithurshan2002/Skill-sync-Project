<x-filament-panels::page>
    @include('filament.shared.error')
    <x-back-link :href="'/'.$area.'/'.($area === 'customer' ? 'bookings' : 'jobs')">Back to {{ $area === 'customer' ? 'bookings' : 'jobs' }}</x-back-link>
    <div class="ss-panel-columns ss-booking-details">
        <div class="ss-stack">
            <section class="ss-card"><div class="ss-section-heading"><span class="ss-eyebrow">BOOKING {{ $booking['id'] }}</span><x-status-badge :status="$booking['status']" /></div><h2>{{ $booking['request']['title'] ?? 'Service booking' }}</h2><p class="ss-description">{{ $booking['request']['description'] ?? '' }}</p><dl class="ss-detail-grid"><div><dt>Appointment</dt><dd>{{ $this->localDate($booking['scheduledAt']) }}</dd></div><div><dt>Location</dt><dd>{{ $booking['request']['town'] ?? '' }}</dd></div><div><dt>Rate basis</dt><dd>LKR {{ number_format($booking['quotedRateLkr']) }} / {{ $booking['rateUnit'] }}</dd></div><div><dt>Service</dt><dd>{{ $booking['request']['category'] ?? 'Service request' }}</dd></div>@if($booking['request']['address'] ?? null)<div><dt>Address</dt><dd>{{ $booking['request']['address'] }}</dd></div>@endif</dl><p class="ss-small ss-muted">This rate is not a final job quote. The final cost is agreed with the professional. Times are shown in Asia/Colombo.</p>
                <dl class="ss-detail-grid"><div><dt>Expected end time</dt><dd>{{ !empty($booking['scheduledEndAt']) ? $this->localDate($booking['scheduledEndAt']) : (!empty($booking['deadlineAt']) ? 'Not recorded; deadline used for booking conflicts' : 'Not recorded; this active booking may block later appointments') }}</dd></div><div><dt>Completion deadline</dt><dd>{{ !empty($booking['deadlineAt']) ? $this->localDate($booking['deadlineAt']) : 'Not recorded for this older booking' }}</dd></div>
                @if(!empty($booking['reportedCompletedAt']))<div><dt>Completion reported</dt><dd>{{ $this->localDate($booking['reportedCompletedAt']) }}</dd></div>@endif
                @if(!empty($booking['confirmedAt']))<div><dt>Customer confirmed</dt><dd>{{ $this->localDate($booking['confirmedAt']) }}</dd></div>@endif
                @if(!empty($booking['cancelledByRole']))<div><dt>Cancelled by</dt><dd>{{ ucfirst($booking['cancelledByRole']) }}</dd></div>@endif</dl>
                <div class="ss-form-actions ss-booking-actions">
                    @if($area === 'customer')
                        @if(in_array($booking['status'], ['pending', 'accepted', 'in_progress'])){{ $this->cancelAction }}@endif
                        @if($booking['status'] === 'awaiting_confirmation'){{ $this->confirmCompletionAction }}{{ $this->disputeCompletionAction }}@endif
                        @if(in_array($booking['status'], ['in_progress', 'awaiting_confirmation', 'completed', 'cancelled']) && empty($booking['complaint'])){{ $this->complaintAction }}@endif
                        @if($booking['status'] === 'completed' && empty($booking['review'])){{ $this->reviewAction }}@endif
                        @if(in_array($booking['status'], ['cancelled', 'rejected']))<a class="ss-btn" href="/customer/requests/{{ $booking['requestId'] }}/recommendations">Find another professional →</a>@endif
                    @else
                        @if($booking['status'] === 'pending'){{ ($this->transitionAction)(['status' => 'accepted'])->label('Accept job')->color('primary') }}{{ ($this->transitionAction)(['status' => 'rejected'])->label('Decline job')->color('danger')->outlined() }}@endif
                        @if($booking['status'] === 'accepted'){{ ($this->transitionAction)(['status' => 'in_progress'])->label('Start job') }}@endif
                        @if($booking['status'] === 'in_progress'){{ ($this->transitionAction)(['status' => 'awaiting_confirmation'])->label('Request completion confirmation')->color('success') }}@endif
                        @if(in_array($booking['status'], ['accepted', 'in_progress'])){{ ($this->transitionAction)(['status' => 'cancelled'])->label('Cancel job')->color('danger')->outlined() }}@endif
                    @endif
                </div>
            </section>
            @if(!empty($booking['complaint']))<section class="ss-card"><h2>Complaint: {{ ucfirst($booking['complaint']['status']) }}</h2><p>{{ $booking['complaint']['reason'] }}</p>@if($booking['complaint']['resolution'])<p><strong>Review decision:</strong> {{ $booking['complaint']['resolution'] }}</p>@else<p class="ss-muted">Waiting for administrator review. This allegation does not affect complaint history until upheld.</p>@endif</section>@endif
            <section class="ss-card"><span class="ss-eyebrow">EVERY STEP, IN ONE PLACE</span><h2>Booking timeline</h2><ol class="ss-timeline">@foreach($booking['history'] as $event)<li><div><x-status-badge :status="$event['status']" /><time>{{ $this->localDate($event['at']) }}</time>@if($event['note'] ?? null)<p>{{ $event['note'] }}</p>@endif</div></li>@endforeach</ol></section>
            @if(!empty($booking['review']))<section class="ss-card"><span class="ss-eyebrow">CUSTOMER FEEDBACK</span><h2>{{ $booking['review']['rating'] }} out of 5 <span class="ss-stars" aria-hidden="true">{{ str_repeat('★', $booking['review']['rating']) }}</span></h2><p class="ss-description">{{ $booking['review']['comment'] }}</p><p class="ss-small ss-muted">{{ $this->localDate($booking['review']['createdAt']) }} · Review saved. The worker rating reflects customer feedback.</p></section>@endif
        </div>
        <aside class="ss-stack">
            <section class="ss-card"><span class="ss-eyebrow">{{ $area === 'customer' ? 'YOUR PROFESSIONAL' : 'ASSIGNED TO YOU' }}</span><div class="ss-worker-identity"><div class="ss-avatar">{{ collect(explode(' ', $booking['worker']['name']))->map(fn($part) => mb_substr($part,0,1))->join('') }}</div><div><h3>{{ $booking['worker']['name'] }}</h3><p class="ss-muted">{{ $booking['worker']['town'] }}</p></div></div><p>{{ implode(' · ', $booking['worker']['categories']) }}</p><a class="ss-text-link" href="/workers/{{ $booking['workerId'] }}">View professional profile ↗</a></section>
            <section class="ss-card ss-soft-card ss-booking-next-step">
                <span class="ss-eyebrow">{{ in_array($booking['status'], ['cancelled', 'rejected']) ? 'BOOKING UPDATE' : 'NEXT STEP' }}</span>
                <h3>{{ match($booking['status']) {
                    'pending' => $area === 'worker' ? 'Review this booking' : 'Waiting for a response',
                    'accepted' => $area === 'worker' ? 'Start when work begins' : 'Your booking is accepted',
                    'in_progress' => $area === 'worker' ? 'Finish and request confirmation' : 'The work is underway',
                    'awaiting_confirmation' => $area === 'customer' ? 'Check the completed work' : 'Waiting for customer confirmation',
                    'completed' => empty($booking['review']) && $area === 'customer' ? 'Share your experience' : 'Booking completed',
                    'rejected' => 'This booking was declined',
                    'cancelled' => 'This booking was cancelled',
                    default => 'Your booking',
                } }}</h3>
                <p class="ss-muted">{{ match($booking['status']) {
                    'pending' => $area === 'worker' ? 'Check the appointment, deadline, and job details, then accept or decline the booking.' : 'The professional will review your request and respond.',
                    'accepted' => $area === 'worker' ? 'Select Start job when you begin working.' : 'Your professional will update the status when work begins.',
                    'in_progress' => $area === 'worker' ? 'When the work is finished, request completion confirmation from the customer.' : 'Your professional will ask you to confirm when the job is finished.',
                    'awaiting_confirmation' => $area === 'customer' ? 'Confirm completion if the work is done, or return the job to in progress if more work is needed.' : 'The customer will confirm completion or return the job for further work. Their response time does not count as late work.',
                    'completed' => empty($booking['review']) ? ($area === 'customer' ? 'Leave a review to help other customers choose a professional.' : 'The customer has confirmed the job is complete.') : 'The job is complete and customer feedback has been recorded.',
                    'rejected', 'cancelled' => $area === 'customer' ? 'Choose another professional for your request when you are ready.' : 'This booking is closed. Return to your jobs to see other requests.',
                    default => 'Follow the timeline for updates to this booking.',
                } }}</p>
            </section>
        </aside>
    </div>
</x-filament-panels::page>
