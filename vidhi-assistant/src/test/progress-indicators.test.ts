import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { ProgressIndicator } from '@/components/ui/progress-indicator';
import { SkeletonLoader } from '@/components/ui/skeleton-loader';
import { TimeoutWarning } from '@/components/ui/timeout-warning';
import { UploadProgress, type UploadFile } from '@/components/ui/upload-progress';

describe('Progress Indicators', () => {
  describe('ProgressIndicator', () => {
    it('renders with default message', () => {
      render(<ProgressIndicator />);
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });

    it('renders with custom message', () => {
      render(<ProgressIndicator message="Processing..." />);
      expect(screen.getByText('Processing...')).toBeInTheDocument();
    });

    it('shows spinner by default', () => {
      const { container } = render(<ProgressIndicator />);
      expect(container.querySelector('.animate-spin')).toBeInTheDocument();
    });

    it('hides spinner when showSpinner is false', () => {
      const { container } = render(<ProgressIndicator showSpinner={false} />);
      expect(container.querySelector('.animate-spin')).not.toBeInTheDocument();
    });

    it('renders progress bar when progress is provided', () => {
      const { container } = render(<ProgressIndicator progress={50} />);
      const progressBar = container.querySelector('[style*="width"]');
      expect(progressBar).toBeInTheDocument();
    });

    it('renders inline variant correctly', () => {
      const { container } = render(<ProgressIndicator variant="inline" message="Loading..." />);
      expect(container.querySelector('.flex.items-center.gap-2')).toBeInTheDocument();
    });

    it('renders compact variant correctly', () => {
      render(<ProgressIndicator variant="compact" message="Loading..." />);
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });
  });

  describe('SkeletonLoader', () => {
    it('renders text variant by default', () => {
      const { container } = render(<SkeletonLoader />);
      expect(container.querySelector('.rounded-lg')).toBeInTheDocument();
    });

    it('renders multiple skeletons based on count', () => {
      const { container } = render(<SkeletonLoader count={3} />);
      const skeletons = container.querySelectorAll('.rounded-lg');
      expect(skeletons.length).toBe(3);
    });

    it('renders message variant with avatar', () => {
      const { container } = render(<SkeletonLoader variant="message" count={2} />);
      const avatars = container.querySelectorAll('.rounded-full');
      expect(avatars.length).toBe(2);
    });

    it('renders card variant with border', () => {
      const { container } = render(<SkeletonLoader variant="card" count={2} />);
      const cards = container.querySelectorAll('.border.border-border');
      expect(cards.length).toBe(2);
    });

    it('renders list variant', () => {
      const { container } = render(<SkeletonLoader variant="list" count={5} />);
      const items = container.querySelectorAll('.h-12');
      expect(items.length).toBe(5);
    });
  });

  describe('TimeoutWarning', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('does not show warning initially', () => {
      render(<TimeoutWarning isLoading={true} warningThreshold={10000} />);
      expect(screen.queryByText(/taking a while/i)).not.toBeInTheDocument();
    });

    it('shows warning after threshold', async () => {
      render(<TimeoutWarning isLoading={true} warningThreshold={5000} />);
      
      vi.advanceTimersByTime(5000);
      
      await waitFor(() => {
        expect(screen.getByText(/taking a while/i)).toBeInTheDocument();
      });
    });

    it('shows critical warning after critical threshold', async () => {
      render(<TimeoutWarning isLoading={true} warningThreshold={5000} criticalThreshold={10000} />);
      
      vi.advanceTimersByTime(10000);
      
      await waitFor(() => {
        expect(screen.getByText(/longer than expected/i)).toBeInTheDocument();
      });
    });

    it('calls onTimeout when critical threshold is reached', async () => {
      const onTimeout = vi.fn();
      render(<TimeoutWarning isLoading={true} warningThreshold={5000} criticalThreshold={10000} onTimeout={onTimeout} />);
      
      vi.advanceTimersByTime(10000);
      
      await waitFor(() => {
        expect(onTimeout).toHaveBeenCalled();
      });
    });

    it('hides warning when loading stops', async () => {
      const { rerender } = render(<TimeoutWarning isLoading={true} warningThreshold={5000} />);
      
      vi.advanceTimersByTime(5000);
      
      await waitFor(() => {
        expect(screen.getByText(/taking a while/i)).toBeInTheDocument();
      });

      rerender(<TimeoutWarning isLoading={false} warningThreshold={5000} />);
      
      expect(screen.queryByText(/taking a while/i)).not.toBeInTheDocument();
    });
  });

  describe('UploadProgress', () => {
    const mockFiles: UploadFile[] = [
      { name: 'document.pdf', size: 1024 * 1024, progress: 50, status: 'uploading' },
      { name: 'image.jpg', size: 512 * 1024, progress: 100, status: 'success' },
      { name: 'contract.docx', size: 2048 * 1024, progress: 0, status: 'error', error: 'Upload failed' }
    ];

    it('renders all files', () => {
      render(<UploadProgress files={mockFiles} />);
      expect(screen.getByText('document.pdf')).toBeInTheDocument();
      expect(screen.getByText('image.jpg')).toBeInTheDocument();
      expect(screen.getByText('contract.docx')).toBeInTheDocument();
    });

    it('formats file sizes correctly', () => {
      render(<UploadProgress files={mockFiles} />);
      expect(screen.getByText('1.0 MB')).toBeInTheDocument();
      expect(screen.getByText('512.0 KB')).toBeInTheDocument();
      expect(screen.getByText('2.0 MB')).toBeInTheDocument();
    });

    it('shows progress bar for uploading files', () => {
      const { container } = render(<UploadProgress files={mockFiles} />);
      const progressBars = container.querySelectorAll('.bg-primary');
      expect(progressBars.length).toBeGreaterThan(0);
    });

    it('shows success message for completed uploads', () => {
      render(<UploadProgress files={mockFiles} />);
      expect(screen.getByText('Upload complete')).toBeInTheDocument();
    });

    it('shows error message for failed uploads', () => {
      render(<UploadProgress files={mockFiles} />);
      expect(screen.getByText('Upload failed')).toBeInTheDocument();
    });

    it('calls onCancel when cancel button is clicked', () => {
      const onCancel = vi.fn();
      render(<UploadProgress files={mockFiles} onCancel={onCancel} />);
      
      const cancelButton = screen.getByText('Cancel');
      cancelButton.click();
      
      expect(onCancel).toHaveBeenCalledWith('document.pdf');
    });

    it('shows different icons for different statuses', () => {
      const { container } = render(<UploadProgress files={mockFiles} />);
      
      // Check for spinner (uploading)
      expect(container.querySelector('.animate-spin')).toBeInTheDocument();
      
      // Check for success icon
      const successIcons = container.querySelectorAll('.text-green-500');
      expect(successIcons.length).toBeGreaterThan(0);
      
      // Check for error icon
      const errorIcons = container.querySelectorAll('.text-destructive');
      expect(errorIcons.length).toBeGreaterThan(0);
    });
  });
});
