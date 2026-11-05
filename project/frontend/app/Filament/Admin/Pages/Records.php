<?php

namespace App\Filament\Admin\Pages;

use App\Filament\Shared\GatewayPage;
use Filament\Actions\Action;
use Filament\Forms\Components\Select;
use Filament\Forms\Components\Textarea;
use Filament\Tables\Columns\TextColumn;
use Filament\Tables\Concerns\InteractsWithTable;
use Filament\Tables\Contracts\HasTable;
use Filament\Tables\Table;
use Illuminate\Contracts\View\View;
use Livewire\Attributes\Url;

class Records extends GatewayPage implements HasTable
{
    use InteractsWithTable;

    protected static string $role = 'admin';

    protected static ?string $slug = 'records';

    protected static ?string $title = 'Records';

    protected static ?string $navigationLabel = 'Manage records';

    protected static string|\BackedEnum|null $navigationIcon = 'heroicon-o-rectangle-stack';

    protected static ?int $navigationSort = 2;

    protected string $view = 'filament.admin.records';

    protected ?string $subheading = 'Review worker applications, maintain categories, and inspect records.';

    #[Url]
    public string $entity = 'workers';

    #[Url]
    public string $recordId = '';

    #[Url]
    public string $detailTab = 'profile';

    #[Url]
    public bool $pendingOnly = false;

    public string $search = '';

    public function updatedEntity(): void
    {
        $this->recordId = '';
        $this->detailTab = 'profile';
        $this->search = '';
        $this->pendingOnly = false;
        $this->resetTable();
    }

    private function matchesFilters(array $record): bool
    {
        $pending = ($record['approvalStatus'] ?? '') === 'pending' && ($record['reviewReady'] ?? false);

        return ($this->entity !== 'workers' || ! $this->pendingOnly || $pending)
            && ($this->search === '' || str_contains(mb_strtolower(json_encode($record)), mb_strtolower($this->search)));
    }

    public function table(Table $table): Table
    {
        return $table->records(function (): array {
            abort_unless(in_array($this->entity, ['workers', 'customers', 'categories', 'requests', 'bookings', 'reviews', 'complaints'], true), 404);

            return collect($this->gateway()->adminRecords(auth()->user(), $this->entity)['data'])
                ->filter(fn (array $record): bool => $this->matchesFilters($record))
                ->keyBy('id')->all();
        })->columns([
            TextColumn::make('displayName')->label('Record')->state(fn (array $record): string => $record['name'] ?? $record['label'] ?? $record['title'] ?? $record['id'])->description(fn (array $record): string => $record['id'])->wrap(),
            TextColumn::make('details')->label('Details')->state(fn (array $record): string => $record['town'] ?? $record['description'] ?? $record['email'] ?? $record['comment'] ?? (isset($record['workerId']) ? 'Worker '.$record['workerId'] : 'Record'))->wrap()->limit(100),
            TextColumn::make('context')->label('Status / context')->state(fn (array $record): string => isset($record['status']) ? ucfirst(str_replace('_', ' ', $record['status'])) : ($this->entity === 'workers' ? ucfirst(str_replace('_', ' ', $record['approvalStatus'] ?? 'pending')) : 'Record'))->badge()->color('gray'),
        ])->recordActions([
            Action::make('details')->label('Details')->icon('heroicon-o-arrow-up-right')->action(function (array $record): void {
                $this->recordId = $record['id'];
                $this->detailTab = 'profile';
            }),
        ])->paginated(false)->emptyStateHeading('No matching records')->emptyStateDescription('Try another search or record type.');
    }

    protected function getViewData(): array
    {
        abort_unless(in_array($this->detailTab, ['profile', 'changes'], true), 404);
        abort_unless(in_array($this->entity, ['workers', 'customers', 'categories', 'requests', 'bookings', 'reviews', 'complaints'], true), 404);
        $all = $this->gateway()->adminRecords(auth()->user(), $this->entity)['data'];
        $selected = $this->recordId ? collect($all)->firstWhere('id', $this->recordId) : null;
        abort_if($this->recordId && ! $selected, 404);
        $records = collect($all)->filter(fn (array $record): bool => $this->matchesFilters($record))->values()->all();

        return compact('records', 'selected');
    }

    public function editCategoryAction(): Action
    {
        return Action::make('editCategory')->label('Edit description')->icon('heroicon-o-pencil-square')->modalHeading('Edit category')
            ->modalDescription('The exact category labels and stable identifiers are preserved for the future classifier.')
            ->fillForm(function (array $arguments) {
                return collect($this->gateway()->adminRecords(auth()->user(), 'categories')['data'])->firstWhere('id', $arguments['id']) ?? abort(404);
            })
            ->schema([Textarea::make('description')->required()->minLength(10)->maxLength(300)->rows(3), Textarea::make('exampleRequest')->label('Example request')->required()->minLength(15)->maxLength(2000)->rows(3)])
            ->action(function (array $arguments, array $data) {
                if ($this->perform(fn () => $this->gateway()->updateCategory(auth()->user(), $arguments['id'], $data))) {
                    $this->success('Category details updated.');
                }
            });
    }

    public function resolveComplaintAction(): Action
    {
        return Action::make('resolveComplaint')->label('Review complaint')
            ->schema([
                Select::make('status')->options(['upheld' => 'Uphold complaint', 'dismissed' => 'Dismiss complaint'])->required(),
                Textarea::make('resolution')->label('Evidence reviewed and reason for decision')->required()->minLength(10)->maxLength(2000),
            ])->action(function (array $arguments, array $data): void {
                if ($this->perform(fn () => $this->gateway()->resolveComplaint(auth()->user(), $arguments['id'], $data))) {
                    $this->success('Complaint reviewed. Both parties have been notified.');
                }
            });
    }

    public function verifyAction(): Action
    {
        return $this->workerReviewAction('verify', 'Review application', 'Review worker application');
    }

    public function reviewChangesAction(): Action
    {
        return $this->workerReviewAction('reviewChanges', 'Review changes', 'Review profile changes');
    }

    private function workerReviewAction(string $name, string $label, string $heading): Action
    {
        return Action::make($name)->label($label)->color('gray')->requiresConfirmation()
            ->modalHeading($heading)->modalSubmitActionLabel('Save decision')
            ->modalContent(fn (): View => $this->actionErrorContent())
            ->modalDescription('Approval makes a complete profile visible and eligible for new bookings. Requesting changes hides it until approved again. Your feedback is visible to the worker.')
            ->schema([
                Select::make('decision')->label('Decision')->options(['approve' => 'Approve profile', 'changes' => 'Request changes / withdraw approval'])->required(),
                Textarea::make('note')->label('Feedback for worker')->required()->minLength(5)->maxLength(500),
            ])
            ->action(function (array $arguments, array $data) {
                if ($this->perform(fn () => $this->gateway()->verifyWorker(auth()->user(), $arguments['id'], $data['decision'] === 'approve', $data['note']), $this->getMountedActionSchema()->getStatePath())) {
                    $this->resetTable();
                    $this->success('Application reviewed. The worker has been notified.');
                }
            });
    }

    public function dataSourceAction(): Action
    {
        return Action::make('dataSource')->label('Set data source')->requiresConfirmation()
            ->modalSubmitActionLabel('Save data source')
            ->modalContent(fn (): View => $this->actionErrorContent())
            ->fillForm(function (array $arguments): array {
                $record = collect($this->gateway()->adminRecords(auth()->user(), $this->entity)['data'])->firstWhere('id', $arguments['id']) ?? abort(404);

                return ['dataSource' => $record['dataSource'] ?? 'test'];
            })
            ->modalDescription('Only enroll verified genuine participants as Real. Both participants must be enrolled before a new booking is real. Existing bookings never change source. Demo identities cannot be promoted.')
            ->schema([
                Select::make('dataSource')->label('Data source')->options(['test' => 'Test', 'demo' => 'Demo (permanent)', 'real' => 'Real — genuine participant'])->required(),
                Textarea::make('note')->label('Verification evidence / reason')->required()->minLength(10)->maxLength(500),
            ])->action(function (array $arguments, array $data): void {
                if ($this->perform(fn () => $this->gateway()->updateDataSource(auth()->user(), $this->entity, $arguments['id'], $data), $this->getMountedActionSchema()->getStatePath())) {
                    $this->resetTable();
                    $this->success('Source updated for future bookings. Historical records were preserved.');
                }
            });
    }

    private function actionErrorContent(): View
    {
        $errorKey = $this->getMountedActionSchema()->getStatePath().'.operation';

        return view('filament.shared.action-error', [
            'operationErrors' => $this->getErrorBag()->get($errorKey),
            'serviceError' => $this->gatewayError,
        ]);
    }
}
