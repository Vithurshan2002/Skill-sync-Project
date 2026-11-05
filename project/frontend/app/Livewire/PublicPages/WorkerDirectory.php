<?php

namespace App\Livewire\PublicPages;

use App\Contracts\SkillSyncGateway;
use Livewire\Attributes\Url;
use Livewire\Component;

class WorkerDirectory extends Component
{
    #[Url(except: '')]
    public string $search = '';

    #[Url(except: '')]
    public string $category = '';

    #[Url(except: '')]
    public string $town = '';

    #[Url(except: false)]
    public bool $available = false;

    #[Url(except: 1)]
    public int $page = 1;

    public function updated(string $property): void
    {
        if ($property !== 'page') {
            $this->page = 1;
        }
    }

    public function clearFilters(): void
    {
        $this->reset('search', 'category', 'town', 'available', 'page');
    }

    public function setPage(int $page): void
    {
        $this->page = max(1, $page);
    }

    public function render()
    {
        $categories = [];
        $workers = [];
        $meta = ['page' => 1, 'perPage' => 6, 'total' => 0];
        $error = null;
        try {
            $gateway = app(SkillSyncGateway::class);
            $categories = $gateway->categories()['data'];
            $result = $gateway->workers([
                'search' => trim($this->search),
                'category' => $this->category,
                'town' => trim($this->town),
                'available' => $this->available ? true : null,
            ], max(1, $this->page), 6);
            $workers = $result['data'];
            $meta = $result['meta'];
        } catch (\Throwable $exception) {
            report($exception);
            $error = 'The worker directory is unavailable right now. Your filters are saved; please try again.';
        }

        return view('livewire.public.worker-directory', compact('categories', 'workers', 'meta', 'error'))
            ->layout('components.layout', ['title' => 'Find a specialist']);
    }
}
